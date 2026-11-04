targetScope = 'resourceGroup'

@description('Lowercase resource prefix; use a unique value per installation.')
@minLength(3)
@maxLength(20)
param prefix string
param location string = resourceGroup().location
@description('GitHub Container Registry image including an explicit release tag or digest.')
param containerImage string
param postgresAdministratorLogin string = 'explorer'
@secure()
param postgresPassword string
@description('Leave empty for a public GitHub Container Registry image; set for a private image.')
param registryUsername string = ''
@secure()
param registryToken string = ''
param additionalAllowedHosts array = []
param vnetAddressPrefix string = '10.70.0.0/16'
param appSubnetPrefix string = '10.70.0.0/23'
param databaseSubnetPrefix string = '10.70.2.0/24'
param postgresSku string = 'Standard_B1ms'
param postgresTier string = 'Burstable'
@minValue(32)
param postgresStorageGb int = 32
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

var appName = '${prefix}-app'
var databaseName = 'remediation'
var postgresName = '${prefix}-pg-${uniqueString(resourceGroup().id, prefix)}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}
resource network 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${prefix}-vnet'
  location: location
  properties: {
    addressSpace: { addressPrefixes: [vnetAddressPrefix] }
    subnets: [
      {
        name: 'container-apps'
        properties: {
          addressPrefix: appSubnetPrefix
          delegations: [
            { name: 'container-apps', properties: { serviceName: 'Microsoft.App/environments' } }
          ]
        }
      }
      {
        name: 'postgres'
        properties: {
          addressPrefix: databaseSubnetPrefix
          delegations: [
            { name: 'postgres', properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' } }
          ]
        }
      }
    ]
  }
}
resource databaseDns 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: '${prefix}.postgres.database.azure.com'
  location: 'global'
}
resource databaseDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: databaseDns
  name: '${prefix}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: network.id }
  }
}
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresName
  location: location
  sku: { name: postgresSku, tier: postgresTier }
  properties: {
    version: '16'
    administratorLogin: postgresAdministratorLogin
    administratorLoginPassword: postgresPassword
    storage: { storageSizeGB: postgresStorageGb }
    backup: { backupRetentionDays: backupRetentionDays, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    network: {
      delegatedSubnetResourceId: '${network.id}/subnets/postgres'
      privateDnsZoneArmResourceId: databaseDns.id
      publicNetworkAccess: 'Disabled'
    }
  }
  dependsOn: [databaseDnsLink]
}
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: databaseName
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      internal: true
      infrastructureSubnetId: '${network.id}/subnets/container-apps'
    }
    workloadProfiles: [ { name: 'Consumption', workloadProfileType: 'Consumption' } ]
  }
}
// This ingress is reachable from the VNet, not the Internet: the environment
// has an internal load balancer. Corporate VPN/peering + DNS are prerequisites.
module appDns './private-dns.bicep' = {
  name: '${prefix}-appdns'
  params: {
    zoneName: environment.properties.defaultDomain
    ipAddress: environment.properties.staticIp
    networkId: network.id
    linkName: '${prefix}-link'
  }
}
var appFqdn = '${appName}.${environment.properties.defaultDomain}'
resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        traffic: [ { latestRevision: true, weight: 100 } ]
      }
      secrets: concat([
        { name: 'postgres-password', value: postgresPassword }
      ], empty(registryUsername) ? [] : [ { name: 'registry-token', value: registryToken } ])
      registries: empty(registryUsername) ? [] : [
        { server: 'ghcr.io', username: registryUsername, passwordSecretRef: 'registry-token' }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: containerImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'REQUIRE_POSTGRES', value: 'true' }
            { name: 'PGHOST', value: postgres.properties.fullyQualifiedDomainName }
            { name: 'PGPORT', value: '5432' }
            { name: 'PGDATABASE', value: databaseName }
            { name: 'PGUSER', value: postgresAdministratorLogin }
            { name: 'PGPASSWORD', secretRef: 'postgres-password' }
            { name: 'PGSSLMODE', value: 'verify-full' }
            { name: 'PGSSLROOTCERT', value: '/etc/ssl/certs/ca-certificates.crt' }
            { name: 'ALLOWED_HOSTS', value: join(concat([appFqdn], additionalAllowedHosts), ',') }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/api/ready', port: 8000, httpHeaders: [ { name: 'Host', value: 'localhost' } ] }
              initialDelaySeconds: 5
              periodSeconds: 5
              timeoutSeconds: 6
              failureThreshold: 30
            }
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000, httpHeaders: [ { name: 'Host', value: 'localhost' } ] }
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: { path: '/api/ready', port: 8000, httpHeaders: [ { name: 'Host', value: 'localhost' } ] }
              periodSeconds: 10
              timeoutSeconds: 6
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
  dependsOn: [database, appDns]
}
output appFqdn string = app.properties.configuration.ingress.fqdn
output privateUrl string = 'https://${appFqdn}'
output virtualNetworkId string = network.id
output postgresFqdn string = postgres.properties.fullyQualifiedDomainName
output postgresDatabase string = databaseName

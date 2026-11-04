targetScope = 'resourceGroup'

@description('Lowercase resource prefix, unique per installation.')
@minLength(3)
@maxLength(20)
param prefix string
param location string = resourceGroup().location
param containerImage string = 'ghcr.io/matte13/data-visualization-tool:1.2.1'
@description('Existing Azure SQL logical-server FQDN; no server/database is created.')
param sqlServerFqdn string = 'dbservertil.${az.environment().suffixes.sqlServerHostname}'
param sqlDatabase string = 'data-visualization-tool-db'
param sqlUser string = 'fuddos'
@secure()
param sqlPassword string
param sqlSchema string = 'dbo'
@description('Existing VNet connected to the existing Azure SQL database.')
param virtualNetworkId string
@description('Existing dedicated subnet delegated to Microsoft.App/environments (at least /27).')
param infrastructureSubnetResourceId string
param registryUsername string = ''
@secure()
param registryToken string = ''
param additionalAllowedHosts array = []

var appName = '${prefix}-app'
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
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
      infrastructureSubnetId: infrastructureSubnetResourceId
    }
    workloadProfiles: [ { name: 'Consumption', workloadProfileType: 'Consumption' } ]
  }
}
module appDns './private-dns.bicep' = {
  name: '${prefix}-appdns'
  params: {
    zoneName: environment.properties.defaultDomain
    ipAddress: environment.properties.staticIp
    networkId: virtualNetworkId
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
        { name: 'azure-sql-password', value: sqlPassword }
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
            { name: 'STORAGE_BACKEND', value: 'azuresql' }
            { name: 'AZURE_SQL_SERVER', value: sqlServerFqdn }
            { name: 'AZURE_SQL_PORT', value: '1433' }
            { name: 'AZURE_SQL_DATABASE', value: sqlDatabase }
            { name: 'AZURE_SQL_USER', value: sqlUser }
            { name: 'AZURE_SQL_SCHEMA', value: sqlSchema }
            { name: 'AZURE_SQL_PASSWORD', secretRef: 'azure-sql-password' }
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
  dependsOn: [appDns]
}
output privateUrl string = 'https://${appFqdn}'
output sqlServer string = sqlServerFqdn
output database string = sqlDatabase

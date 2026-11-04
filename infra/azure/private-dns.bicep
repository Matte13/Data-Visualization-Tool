// Nested deployment: the environment's default domain is known after creation.
param zoneName string
param ipAddress string
param networkId string
param linkName string
resource zone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: zoneName
  location: 'global'
}
resource link 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: zone
  name: linkName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: networkId }
  }
}
resource record 'Microsoft.Network/privateDnsZones/A@2020-06-01' = {
  parent: zone
  name: '*'
  properties: { ttl: 300, aRecords: [ { ipv4Address: ipAddress } ] }
}

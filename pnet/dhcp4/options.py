import sys
import enum


if sys.version_info >= (3, 0):
    ord = lambda x: x


class DHCPOption(enum.IntEnum):
    Padding = 0
    SubnetMask = 1
    TimeOffset = 2
    Router = 3
    TimeServer = 4
    NameServer = 5
    DomainNameServer = 6
    LogServer = 7
    CookieServer = 8
    LPRServer = 9
    ImpressServer = 10
    ResourceLocationServer = 11
    HostName = 12
    BootFileSize = 13
    MeritDumpFile = 14
    DomainName = 15
    SwapServer = 16
    RootPath = 17
    ExtensionsPath = 18
    IPForwardingEnableDisable = 19
    NonLocalSourceRoutingEnableDisable = 20
    PolicyFilter = 21
    MaximumDatagramReassemblySize = 22
    DefaultIPTimeToLive = 23
    PathMTUAgingTimeout = 24
    PathMTUPlateauTable = 25
    InterfaceMTU = 26
    AllSubnetsAreLocal = 27
    BroadcastAddress = 28
    PerformMaskDiscovery = 29
    MaskSupplier = 30
    PerformRouterDiscovery = 31
    RouterSolicitationAddress = 32
    StaticRoute = 33
    TrailerEncapsulation = 34
    ARPCacheTimeout = 35
    EthernetEncapsulation = 36
    TCPDefaultTTL = 37
    TCPKeepaliveInterval = 38
    TCPKeepaliveGarbage = 39
    NetworkInformationServiceDomain = 40
    NetworkInformationServers = 41
    NetworkTimeProtocolServers = 42
    VendorSpecificInformation = 43
    NetBIOSOverTCPIPNameServer = 44
    NetBIOSOverTCPIPDatagramDistributionServer = 45
    NetBIOSOverTCPIPNodeType = 46
    NetBIOSOverTCPIPScope = 47
    XWindowSystemFontServer = 48
    XWindowSystemDisplayManager = 49
    RequestedIPAddress = 50
    IPAddressLeaseTime = 51
    Overload = 52
    DHCPMessageType = 53
    ServerIdentifier = 54
    ParameterRequestList = 55
    Message = 56
    MaximumDHCPMessageSize = 57
    RenewalTimeValue = 58
    RebindingTimeValue = 59
    VendorClassIdentifier = 60
    ClientIdentifier = 61
    NetworkInformationServicePlusDomain = 64
    NetworkInformationServicePlusServers = 65
    TFTPServerName = 66
    BootFileName = 67
    MobileIPHomeAgent = 68
    SimpleMailTransportProtocol = 69
    PostOfficeProtocolServer = 70
    NetworkNewsTransportProtocol = 71
    DefaultWorldWideWebServer = 72
    DefaultFingerServer = 73
    DefaultInternetRelayChatServer = 74
    StreetTalkServer = 75
    StreetTalkDirectoryAssistance = 76
    UserClass = 77
    RelayAgentInformation = 82
    ClientArchitecture = 93
    TZPOSIXString = 100
    TZDatabaseString = 101
    DomainSearchOptionFormat = 119
    ClasslessRouteFormat = 121
    End = 255


class Options(list):
    def __bytes__(self):
        return self.tobytes()

    def tobytes(self):
        options = bytearray()

        for op, payload in self:
            options.extend([op, len(payload)])
            options.extend(payload)

        options.append(DHCPOption.End)
        return bytes(options)

    @classmethod
    def parse(cls, payload):
        orig_payload = payload
        options = []

        while payload:
            op = DHCPOption(ord(payload[0]))
            if op == DHCPOption.End:
                break

            length = ord(payload[1])
            contents = payload[2:length+2]
            options.append((op, contents))
            payload = payload[length+2:]

        return cls(options)

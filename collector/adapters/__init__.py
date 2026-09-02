from collector.adapters.campuspick import CampuspickAdapter
from collector.adapters.dacon import DaconAdapter
from collector.adapters.linkareer import LinkareerAdapter
from collector.adapters.thinkyou import ThinkyouAdapter
from collector.adapters.wevity import WevityAdapter

ADAPTERS = [
    WevityAdapter(),
    ThinkyouAdapter(),
    LinkareerAdapter(),
    DaconAdapter(),
    CampuspickAdapter(),
]

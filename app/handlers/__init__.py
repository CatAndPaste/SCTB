from .start import register_start_handlers
from .registration import register_registration_handlers
from .subscription import register_subscription_handlers
from .commands import register_command_handlers

def register_handlers(dp):
    register_start_handlers(dp)
    register_registration_handlers(dp)
    register_subscription_handlers(dp)
    register_command_handlers(dp)

from .subscription_middleware import SubscriptionMiddleware

def setup_middlewares(dp):
    dp.update.middleware(SubscriptionMiddleware())

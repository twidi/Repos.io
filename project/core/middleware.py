# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from core.core_utils import get_user_accounts

class FetchFullCurrentAccounts(object):
    """
    Middleware that try to make a fetch full for all accounts of the current user
    """

    def process_request(self, request):
        accounts = get_user_accounts()
        if accounts:
            for account in accounts:
                account.fetch_full(
                    token = account.get_default_token(),
                    depth = 1,
                    async = True,
                    async_priority = 1
                )

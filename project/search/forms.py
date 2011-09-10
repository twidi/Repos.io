from haystack.forms import SearchForm as BaseSearchForm

from core.models import Repository, Account

class RepositorySearchForm(BaseSearchForm):

    def search(self):
        sqs = super(RepositorySearchForm, self).search()
        return sqs.models(Repository)


class AccountSearchForm(BaseSearchForm):

    def search(self):
        sqs = super(AccountSearchForm, self).search()
        return sqs.models(Account)

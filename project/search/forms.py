from haystack.forms import SearchForm as BaseSearchForm

from core.models import Repository

class RepositorySearchForm(BaseSearchForm):

    def search(self):
        sqs = super(RepositorySearchForm, self).search()
        return sqs.models(Repository)


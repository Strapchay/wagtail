import django_filters
from django import forms
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy

from wagtail.admin.views.generic import history
from wagtail.admin.views.pages.utils import get_breadcrumbs_items_for_page
from wagtail.models import Page, PageLogEntry
from wagtail.permissions import page_permission_policy


class PageHistoryFilterSet(history.HistoryFilterSet):
    hide_commenting_actions = django_filters.BooleanFilter(
        label=gettext_lazy("Hide commenting actions"),
        method="filter_hide_commenting_actions",
        widget=forms.CheckboxInput,
    )

    def filter_hide_commenting_actions(self, queryset, name, value):
        if value:
            queryset = queryset.exclude(action__startswith="wagtail.comments")
        return queryset


class PageWorkflowHistoryViewMixin:
    model = Page
    pk_url_kwarg = "page_id"

    def dispatch(self, request, *args, **kwargs):
        if not self.object.permissions_for_user(request.user).can_edit():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, page=self.object)


class WorkflowHistoryView(PageWorkflowHistoryViewMixin, history.WorkflowHistoryView):
    header_icon = "doc-empty-inverse"
    workflow_history_url_name = "wagtailadmin_pages:workflow_history"
    workflow_history_detail_url_name = "wagtailadmin_pages:workflow_history_detail"


class WorkflowHistoryDetailView(
    PageWorkflowHistoryViewMixin, history.WorkflowHistoryDetailView
):
    object_icon = "doc-empty-inverse"
    workflow_history_url_name = "wagtailadmin_pages:workflow_history"


class PageHistoryView(history.HistoryView):
    template_name = "wagtailadmin/pages/history.html"
    filterset_class = PageHistoryFilterSet
    model = Page
    pk_url_kwarg = "page_id"
    permission_policy = page_permission_policy
    any_permission_required = {
        "add",
        "change",
        "publish",
        "bulk_delete",
        "lock",
        "unlock",
    }
    history_url_name = "wagtailadmin_pages:history"
    history_results_url_name = "wagtailadmin_pages:history_results"
    edit_url_name = "wagtailadmin_pages:edit"
    revisions_view_url_name = "wagtailadmin_pages:revisions_view"
    revisions_revert_url_name = "wagtailadmin_pages:revisions_revert"
    revisions_compare_url_name = "wagtailadmin_pages:revisions_compare"
    revisions_unschedule_url_name = "wagtailadmin_pages:revisions_unschedule"
    _show_breadcrumbs = True

    def get_object(self):
        return get_object_or_404(Page, id=self.pk).specific

    def get_page_subtitle(self):
        return self.object.get_admin_display_title()

    def user_can_unschedule(self):
        return self.object.permissions_for_user(self.request.user).can_unschedule()

    def get_base_queryset(self):
        return self._annotate_queryset(PageLogEntry.objects.filter(page=self.object))

    @cached_property
    def breadcrumbs_items(self):
        return get_breadcrumbs_items_for_page(self.object, self.request.user)

    def get_breadcrumbs_items(self):
        # The generic HistoryView will add an edit link for the current object as
        # the second-to-last item, but we don't want that because we want to
        # link to the explore view instead for consistency with how page
        # breadcrumbs work elsewhere. So we only take the last item, which is
        # the "self" (History) item.
        return self.breadcrumbs_items + [super().get_breadcrumbs_items()[-1]]

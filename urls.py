from django.conf.urls import url

from GeoExcel.views import excel_upload, configureTable, submitTable, searchTables, searchTableKey, excel_begin, addNewEntries

urlpatterns = [
    url(r'^upload$', excel_upload, name='excel_upload'),
    url(r'^upload/begin$', excel_begin, name='excel_begin'),
    url(r'^create/configure$', configureTable, name='configureTable'),
    url(r'^create/submit$', submitTable, name='submitTable'),
    url(r'^search/tables$', searchTables, name='searchTables'),
    url(r'^search/tablekey$', searchTableKey, name='searchTableKey'),
    url(r'^add$', addNewEntries, name='addNewEntries'),
]
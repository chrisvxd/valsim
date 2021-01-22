from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'valsim.views.page', name='valsim_page'),
    url(r'^image', 'valsim.views.image', name='valsim_image'),
)
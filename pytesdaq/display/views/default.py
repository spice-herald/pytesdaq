from pyramid.view import (
    view_config,
    view_defaults
    )

from .. import db

server = db.MySQLCore()


@view_defaults(renderer='../templates/home.mako')
class MainViews:
    def __init__(self, request):
        self.request = request

    @view_config(route_name='home', renderer='../templates/home.mako')
    def home(self):
        return {'name': 'Home View'}

    server.connect_test()

    serieslist = server.query('test_data')

    server.disconnect()


    @view_config(route_name='series_test', renderer='../templates/series_test.mako')
    def series_test(self):

        def search(dic):
            return dic['series_num']

        MainViews.serieslist.sort(key=search)
        return {'name': 'Series_Test', 'series': MainViews.serieslist}

    @view_config(route_name='series_info', renderer='../templates/series_info.mako')
    def series_info(self):

        series_num = self.request.matchdict['series_num'] #fix if we get 'id'
        
        ind_series = next(item for item in MainViews.serieslist if item["series_num"] == str(series_num))
        finalseries = ind_series
        return {'name': str(series_num), 'this_series': finalseries}
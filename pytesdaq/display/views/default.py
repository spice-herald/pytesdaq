from pyramid.view import (
    view_config,
    view_defaults
    )

@view_defaults(renderer='../templates/home.mako')
class MainViews:
    def __init__(self, request):
        self.request = request

    @view_config(route_name='home', renderer='../templates/home.mako')
    def home(self):
        return {'name': 'Home View'}

    series = dict() #self.request.matchdict["series"]
    serieslist = []
    for i in range(20):
        series_num = 120203401161777 + 10* i
        new_series = {'series_num': series_num, 'run_type': 2*i - 1, 'timestamp': 1531053235 + 2*i, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 531 + 7*i}
        series[str(series_num)] = new_series
        serieslist.append(new_series)

    @view_config(route_name='series_test', renderer='../templates/series_test.mako')
    def series_test(self):

        def search(dic):
            return dic['series_num']

        MainViews.serieslist.sort(key=search)
        return {'name': 'Series_Test', 'series': MainViews.serieslist}

    @view_config(route_name='series_info', renderer='../templates/series_info.mako')
    def series_info(self):

        series_num = self.request.matchdict['series_num']
        
        finalseries = MainViews.series[str(series_num)]
        return {'name': str(series_num), 'this_series': finalseries}
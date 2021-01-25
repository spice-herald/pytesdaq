from pyramid.view import (
    view_config,
    view_defaults
    )
import db.py

@view_defaults(renderer='../templates/home.mako')
class TutorialViews:
    def __init__(self, request):
        self.request = request

    @view_config(route_name='home', renderer='../templates/home.mako')
    def home(self):
        return {'name': 'Home View'}

    @view_config(route_name='series_test', renderer='../templates/series_test.mako')
    def series_test(self):

        series = self.request.matchdict["series"]
        for i in range(20):
            new_series = {'series_num': 120203401161777 + 10* i, 'run_type': 2*i - 1, 'timestamp': 1531053235 + 2*i, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 531 + 7*i}
            series.append(new_series)

        def search(dic):
            return dic['series_num']

        series.sort(key=search)
        return {'name': 'Series_Test', 'series': series}
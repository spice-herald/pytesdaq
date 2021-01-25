from pyramid.view import (
    view_config,
    view_defaults
    )

@view_defaults(renderer='series_test.mako')
class TutorialViews:
    def __init__(self, request):
        self.request = request

    @view_config(route_name='home')
    def home(self):
        series1 = {'series_num': 120200601161750, 'run_type': 1, 'timestamp': 1591053471, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 525}
        series2 = {'series_num': 120203401161721, 'run_type': 1, 'timestamp': 1531053454, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 526}

        series3 = {'series_num': 120203401161777, 'run_type': 2, 'timestamp': 1531053234, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 531}

        series = [series1, series2, series3]
        return {'name': 'Home View', 'series_list': series}

    @view_config(route_name='series_test', renderer='/templates/series_test.mako')
    def series_test(self):
        series1 = {'series_num': 120200601161750, 'run_type': 1, 'timestamp': 1591053471, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 525}
        series2 = {'series_num': 120203401161721, 'run_type': 1, 'timestamp': 1531053454, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 526}

        series3 = {'series_num': 120203401161777, 'run_type': 2, 'timestamp': 1531053234, 
            'comment': 'Data Challenge 1. 4 channels at 1.25 MHz for 5 hour. All channels at GS. A function generator feeds a sine wave to channel 0. Channel 1 and trigger on PFI0 are identical. Channel 2 is left open. CHannel 3 has a termination resistor of 50 ohm. Data taken with Cfg_Default as termination option in driver. ', 
            'nb_events': 531}

        series = [series1, series2, series3]
        return {'name': 'Series_Test', 'series_list': series}
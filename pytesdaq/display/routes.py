def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('series_test', '/series_test')
    config.add_route('series_info', '/series/{series_num}')

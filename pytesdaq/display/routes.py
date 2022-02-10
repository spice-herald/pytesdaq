def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('series_test', '/series_test')
    config.add_route('series_info', '/group/{group_name}/{series_num}', '/{series_num}')
    config.add_route('group_info', '/group/{group_name}')
    config.add_route('groups', '/group')

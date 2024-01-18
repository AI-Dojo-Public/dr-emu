class Agent:
    create_git = "/agents/create/git/"
    create_local = "/agents/create/local/"
    create_pypi = "/agents/create/pypi/"
    delete = "/agents/delete/{}/"
    list = "/agents/"
    update = "/agents/update/{}/"


class Template:
    list = "/templates/"
    create = "/templates/create/"
    delete = "/templates/delete/{}/"


class Run:
    create = "/runs/create/"
    delete = "/runs/delete/{}/"
    stop = "/runs/stop/{}/"
    start = "/runs/start/{}/"
    list = "/runs/"


class Infrastructure:
    get = "/infrastructure/get/{}/"
    delete = "/infrastructure/delete/{}/"
    list = "/infrastructure/list/"

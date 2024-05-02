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
    get = "/runs/get/{}/"


class Infrastructure:
    get = "/infrastructures/get/{}/"
    delete = "/infrastructures/delete/{}/"
    list = "/infrastructures/"

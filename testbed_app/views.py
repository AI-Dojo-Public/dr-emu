from testbed_app.resources import templates


async def home(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context=context)


async def build_infra(request):
    pass


async def destroy_infra(request):
    pass


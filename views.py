import uuid
import os
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

SUBMIT_PAGE_HTML = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\"        \"http://www.w3.org/TR/html4/loose.dtd\"><html><head>    <title>2D VAL Simulator</title></head><body>    This is only intending for basic 2D models and is by no means perfect.    Things it doesn't do:    <ul>        <li>DO...UNTIL</li>        <li>Subtracting, multiplying, dividing or any maths logic other than a simple + when setting a variable</li>    </ul>    <italic>This is only intended for ES372 Students for the Robot Lab. Sorry to those who missed out...</italic>    <br/><br/><br/>    <form method=\"post\" action=\"\">        <b>Enter your code here...</b><br/>        <textarea name=\"code\" cols=\"50\" rows=\"50\"></textarea><br>        <input type=\"submit\" value=\"Submit\" />    </form></body></html>"
RESPONSE_PAGE_HTML = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\"        \"http://www.w3.org/TR/html4/loose.dtd\"><html><head>    <title>Results</title></head><body>    <img src=\"%s\"></img><br/>    <br/><span style='margin-left:225px'>SIMULATION OUTPUT:</span><br/> <textarea style='margin-left:75px' cols=100 rows=100>%s</textarea><br/>ID: %s</body></html>"

import sys
import valsim # need to reimport each time


# a simple class with a write method
class WritableObject:
    def __init__(self):
        self.content = []
    def write(self, string):
        self.content.append(string)

# example with redirection of sys.stdout
foo = WritableObject()                   # a writable object

@csrf_exempt
def page(request):
    if request.POST:

        code = request.POST.get('code')
        if not code:
            return HttpResponse(status=500)

        random_number = str(uuid.uuid4())
        code_path = os.path.abspath('valsim/media/%s.v2' % random_number)
        log_path = os.path.abspath('valsim/media/%s.log' % random_number)
        png_path = os.path.abspath('valsim/media/%s.png' % random_number)

        with open(code_path, 'w') as f:
            f.write(code.replace('\r', ''))

        reload(valsim)

        plot = valsim.Plotter((0,0,0))

        original_out = sys.stdout
        sys.stdout = foo # redirection

        try:
            try:
                valsim.process_line(plot, 'SET P0 = datum')
                valsim.process_line(plot, 'EXECUTE %s' % code_path)
                plot.plot()
                valsim.plt.savefig(png_path)
            except RuntimeError:
                return HttpResponse(content='Your code has an <b>infinite loop</b> in it and cannot be executed!<br/> ID %s' % random_number)
        except Exception, e:
            return HttpResponse(content='Your code has an error.<br/>Error Msg: %s</b><br/>ID: %s' % (e.message, random_number))

        sys.stdout = original_out

        with open(log_path, 'w+') as f:
            for l in foo.content:
                f.write(l)

        log_str = '\n'.join(foo.content).replace('\n\n', '\n')
        foo.content = []

        with open(png_path, 'r') as png_fo:
            png = png_fo.read()


        return HttpResponse(content=RESPONSE_PAGE_HTML % ('image?uuid=%s' % random_number, log_str, random_number))

    else:
        return HttpResponse(content=SUBMIT_PAGE_HTML)

def image(request):
    image_uuid = request.GET.get('uuid')

    png_path = os.path.abspath('valsim/media/%s.png' % image_uuid)

    with open(png_path, 'r') as png_fo:
        png = png_fo.read()

    return HttpResponse(content=png,  mimetype="image/png")


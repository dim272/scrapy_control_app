# web management interface
import threading
import time

from flask import Flask, render_template, request
from turbo_flask import Turbo

from control import Control

turbo = Turbo()
control = Control()


def create_app():
    app = Flask(__name__, template_folder='./templates', static_folder='./static')
    app.config['SERVER_NAME'] = '127.0.0.1:5000'
    turbo.init_app(app)

    return app


app = create_app()


@app.before_first_request
def before_first_request():
    threading.Thread(target=update_load).start()


def update_load():
    with app.app_context():
        while True:
            time.sleep(10)
            control.collect_status()
            turbo.push(turbo.replace(render_template('index.html'), control.status))


@app.route('/')
def index():
    return render_template('index.html', data=control.status)


@app.route('/control_button', methods=['POST'])
def success():
    if request.method == 'POST':
        if request.form.get("start"):
            spider = request.form.get("start")
            category = spider.split('.')[0]
            spider_name = spider.split('.')[1]
            control.start_spider(category, spider_name)
        else:
            spider = request.form.get("stop")
            pid = spider.split(':')[-1]
            control.stop_spider(pid)
            print('Stop', spider, pid)
        return render_template('index.html', data=control.status)


if __name__ == '__main__':
    app.run()

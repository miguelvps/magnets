import time
import libtorrent as lt
from werkzeug.urls import url_decode, url_unquote
from flask import Flask, Response, request, render_template
from flaskext.cache import Cache

DEBUG = True
CACHE_TYPE = 'simple'
CACHE_THRESHOLD = 1000

app = Flask(__name__)
app.config.from_object(__name__)
cache = Cache(app)

ses = lt.session()
ses.listen_on(6881, 6891)


def create_torrent(info):
    entry = {'info': lt.bdecode(info.metadata())}
    trackers = [tracker.url for tracker in info.trackers()]
    if trackers:
        entry['announce'] = trackers[0]
        if len(trackers) > 1:
            entry['announce-list'] = trackers
    return (info.name() + ".torrent", lt.bencode(entry))


@app.route('/')
def index():
    if request.args.has_key('magnet'):
        magnet = url_unquote(request.args['magnet']).encode(request.charset)
        magnet_xt = url_decode(magnet[magnet.index("?") + 1:])['xt']
        torrent = cache.get(magnet_xt)
        if not torrent:
            try:
                handle = lt.add_magnet_uri(ses, magnet,
                                           {'save_path': "./invalid",
                                            'paused': False,
                                            'auto_managed': False,
                                            'duplicate_is_error': False})
                while not handle.has_metadata():
                    time.sleep(0.01)
                handle.pause()
                info = handle.get_torrent_info()
                torrent = create_torrent(info)
                cache.set(magnet_xt, torrent)
                ses.remove_torrent(handle, lt.options_t.delete_files)
            except:
                torrent = cache.get(magnet_xt)
        response = Response(response=torrent[1], mimetype='application/x-bittorrent')
        response.headers.add('Content-Disposition', 'attachment',
                             filename=torrent[0])
        return response
    return render_template('index.html')


if __name__ == '__main__':
    app.run()

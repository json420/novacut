"use strict";

var id = window.location.hash.slice(1);

var doc = novacut.get_sync(id);
var db = new couch.Database(doc.db_name);
var doc = db.get_sync(id);


function css_url(url) {
    return ['url(', JSON.stringify(url), ')'].join('');
}

//thumb.style.backgroundImage


var UI = {
    init: function() {
        set_title('title', doc.title);
        var seq = db.get_sync(doc.root_id);
        console.log(seq);
        db.post(UI.on_rows, {keys: seq.node.src}, '_all_docs', {include_docs: true});

    },

    on_rows: function(req) {
        var rows = req.read().rows;
        var sequence = $('sequence');
        rows.forEach(function(row) {
            var slice = $el('div', {'class': 'slice', 'id': row.id});
            var node = row.doc.node;

            var start = $el('div', {textContent: (node.start.frame + 1)});
            start.style.backgroundImage = css_url(
                ['/thumbnails', node.src, node.start.frame].join('/')
            );
            slice.appendChild(start);

            var stop = $el('div', {textContent: node.stop.frame});
            stop.style.backgroundImage = css_url(
                ['/thumbnails', node.src, (node.stop.frame - 1)].join('/')
            );
            slice.appendChild(stop);

            sequence.appendChild(slice);
        });
    },
}

window.addEventListener('load', UI.init);

Hub.connect('render_finished',
    function(job_id, file_id) {
        var player = $('player');
        player.src = 'dmedia:' + file_id;
        player.play();
    }
);

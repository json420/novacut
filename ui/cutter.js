"use strict";

var id = window.location.hash.slice(1);

var doc = novacut.get_sync(id);
var db = new couch.Database(doc.db_name);
var doc = db.get_sync(id);


var UI = {
    init: function() {
        set_title('title', doc.title);
        var root = db.get(
        db.get(UI.on_rows, '_all_docs');
    },

    on_rows: function(req) {
        var rows = req.read().rows;
        rows.forEach(function(row) {
            console.log(row.id);
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

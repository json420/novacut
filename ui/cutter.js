"use strict";

var id = window.location.hash.slice(1);

var doc = novacut.get_sync(id);
var db = new couch.Database(doc.db_name);
var doc = db.get_sync(id);


var UI = {
    init: function() {
        set_title('title', doc.title);

//        var p = new Project(dmedia);
//        var rows = p.db.view_sync('doc', 'type', {key: 'dmedia/file', reduce: false, limit: 20}).rows;
//        var doc_ids = [];
//        rows.forEach(function(row) {
//            doc_ids.push(row.id);
//        });
//        Hub.send('copy_docs', p.db.name, db.name, doc_ids);

        Hub.send('render', id, doc['root_id'], null);
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

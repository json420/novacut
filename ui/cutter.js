"use strict";

var id = window.location.hash.slice(1);

var doc = novacut.get_sync(id);
var db = new couch.Database(doc.db_name);


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
    },

}

window.addEventListener('load', UI.init);

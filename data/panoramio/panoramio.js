var map;

function python(command) {
    console.log('Python command: ' + command);
    window.status = new Date().getTime() + '|' + command;
}

function initialize() {
    var mapOptions = {
        zoom: 1,
        center: new google.maps.LatLng(0, 20)
        //mapTypeId: google.maps.MapTypeId.SATELLITE
    };

    map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);

    var panoramioLayer = new google.maps.panoramio.PanoramioLayer();
    panoramioLayer.setMap(map);

    // Create the search box and link it to the UI element.
    var input = document.getElementById('search');
    map.controls[google.maps.ControlPosition.TOP_LEFT].push(input);
    var searchBox = new google.maps.places.SearchBox(input);

    // Listen for the event fired when the user selects an item from the
    // pick list. Retrieve the matching places for that item.
    google.maps.event.addListener(searchBox, 'places_changed', function () {
        var places = searchBox.getPlaces();

        if (places.length == 0) {
            return;
        }

        var bounds = new google.maps.LatLngBounds();
        for (var i = 0, place; place = places[i]; i++) {
            if (place.geometry.viewport) {
                bounds.union(place.geometry.viewport);
            } else {
                bounds.extend(place.geometry.location);
            }
        }

        map.fitBounds(bounds);
    });

    // Bias the SearchBox results towards places that are within the bounds of the
    // current map's viewport.
    google.maps.event.addListener(map, 'bounds_changed', function () {
        var bounds = map.getBounds();
        searchBox.setBounds(bounds);
    });

    google.maps.event.addListenerOnce(map, 'idle', function () {
        document.getElementById('search').style.display = 'block';
    });
}

function setLocation(json) {
    var l = JSON.parse(json, jsonReviver);
    map.setZoom(l["zoom"]);
    map.setCenter(l["center"]);
    if (l["search"]) {
        document.getElementById('search').value = l["search"];
    }
}

function reportLocation() {
    var search = document.getElementById('search').value.trim();
    var data = _.extend((search ? {search: search} : {}), {
        zoom: map.getZoom(),
        center: map.getCenter(),
        minx: map.getBounds().getSouthWest().lng(),
        miny: map.getBounds().getSouthWest().lat(),
        maxx: map.getBounds().getNorthEast().lng(),
        maxy: map.getBounds().getNorthEast().lat()
    });
    var json = JSON.stringify(data, jsonReplacer);
    console.log("Reporting location: " + json);
    python('location:' + json);
}

function jsonReplacer(k, v) {
    if (v instanceof google.maps.LatLng) {
        return {lat: v.lat(), lng: v.lng()};
    } else if (v instanceof google.maps.LatLngBounds) {
        return {sw: v.getSouthWest(), ne: v.getNorthEast()}
    }
    return v;
}

function jsonReviver(k, v) {
    if (_.isEqual(_.isObject(v) && _.keys(v).sort(), ['lat', 'lng'])) {
        return new google.maps.LatLng(v.lat, v.lng);
    } else if (_.isEqual(_.isObject(v) && _.keys(v).sort(), ['sw', 'ne'])) {
        return new google.maps.LatLngBounds(v.sw, v.ne);
    }
    return v;
}

google.maps.event.addDomListener(window, 'load', initialize);


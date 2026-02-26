$(function(){
    $('#district').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
        $('#location').val(districtid);
        $('#municipality').empty();
        $('#municipality').append("<option value='' selected='selected'>Select Municipality</option>");
        $('#subcounty').empty();
        $('#subcounty').append("<option value='' selected='selected'>Select Sub County</option>");
        $('#facility').empty();
        $('#facility').append("<option value='' selected='selected'>Select Health Facility</option>");
		$.get(
            '/api/v1/loc_children/' + districtid,
            {},
            function(data){
                var municipalities = data;
                for(var i in municipalities){
                    val = municipalities[i]["id"];
                    txt = municipalities[i]["name"];
                    $('#municipality').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
        $.get(
            '/api/v1/district_facilities/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var facilities = data;
                for(var i in facilities){
                    val = facilities[i]["id"];
                    txt = facilities[i]["name"];
                    $('#facility').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
    });

    $('#municipality').change(function(){
        var municipalityId = $(this).val();
        if (municipalityId == '0' || municipalityId == '')
            return;
        $('#location').val(municipalityId);
        $('#subcounty').empty();
        $('#subcounty').append("<option value='' selected='selected'>Select Sub County</option>");
        $('#facility').empty();
        $('#facility').append("<option value='' selected='selected'>Select Health Facility</option>");
        $.get('/api/v1/loc_children/' + municipalityId,
            {xtype:'municipality', xid: municipalityId},
            function (data){
                var facilities = [];
                var subcounties = data;
                var requests = [];
                for (var i in subcounties){
                    val = subcounties[i]['id'];
                    txt = subcounties[i]['name'];
                    $('#subcounty').append(
                        $(document.createElement("option")).attr("value", val).text(txt)
                    );

                    var req = $.get('/api/v1/loc_facilities/' + val, {}, null, 'json');
                    requests.push(req);
                }
                $.when.apply($, requests).done(function(){
                    var results = arguments.length === 1 ? [arguments] : arguments;
                    for (var i = 0; i < results.length; i++) {
                        // Each result is [data, statusText, jqXHR]
                        var data = results[i][0];
                        facilities = facilities.concat(data);
                    }
                    for (var i in facilities) {
                        var val = facilities[i]['id'];
                        var txt = facilities[i]['name'];
                        $('#facility').append(
                            $(document.createElement("option")).attr("value", val).text(txt)
                        );
                    }
                });

            },
            'json'
        );

    });

	$('#subcounty').change(function(){
        var subcountyid = $(this).val();
        if (subcountyid == '0' || subcountyid == '')
            return;
        $('#location').val(subcountyid);
        $('#facility').empty();
        $('#facility').append("<option value='' selected='selected'>Select Health Facility</option>");
        $.get(
            '/api/v1/loc_facilities/' + subcountyid,
            {},
            function(data){
                var facilities = data;
                for(var i in facilities){
                    val = facilities[i]['id'];
                    txt = facilities[i]['name'];
                    $('#facility').append(
                            $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
	});


    $('#district_1').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
         $('#municipality1').empty();
        $('#municipality1').append("<option value='' selected='selected'>Select Municipality</option>");
        $('#subcounty_1').empty();
        $('#subcounty_1').append("<option value='' selected='selected'>Select Sub County</option>");
        $('#sms_facility').empty();
        $('#sms_facility').append("<option value='' selected='selected'>Select Health Facility</option>");
		$.get(
            '/api/v1/loc_children/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var municipalities = data;
                console.log("####", municipalities);
                for(var i in municipalities){
                    val = municipalities[i]["id"];
                    txt = municipalities[i]["name"];
                    $('#municipality1').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
        $.get(
            '/api/v1/district_facilities/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var facilities = data;
                for(var i in facilities){
                    val = facilities[i]["id"];
                    txt = facilities[i]["name"];
                    $('#sms_facility').append(
                        $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
    });

     $('#municipality1').change(function(){
        var municipalityId = $(this).val();
        if (municipalityId == '0' || municipalityId == '')
            return;
        // $('#location').val(municipalityId);
        $('#subcounty_1').empty();
        $('#subcounty_1').append("<option value='' selected='selected'>Select Sub County</option>");
        $('#sms_facility').empty();
        $('#sms_facility').append("<option value='' selected='selected'>Select Health Facility</option>");
        $.get('/api/v1/loc_children/' + municipalityId,
            {xtype:'municipality', xid: municipalityId},
            function (data){
                var facilities = [];
                var subcounties = data;
                var requests = [];
                for (var i in subcounties){
                    val = subcounties[i]['id'];
                    txt = subcounties[i]['name'];
                    $('#subcounty_1').append(
                        $(document.createElement("option")).attr("value", val).text(txt)
                    );

                    var req = $.get('/api/v1/loc_facilities/' + val, {}, null, 'json');
                    requests.push(req);
                }
                $.when.apply($, requests).done(function(){
                    var results = arguments.length === 1 ? [arguments] : arguments;
                    for (var i = 0; i < results.length; i++) {
                        // Each result is [data, statusText, jqXHR]
                        var data = results[i][0];
                        facilities = facilities.concat(data);
                    }
                    for (var i in facilities) {
                        var val = facilities[i]['id'];
                        var txt = facilities[i]['name'];
                        $('#sms_facility').append(
                            $(document.createElement("option")).attr("value", val).text(txt)
                        );
                    }
                });

            },
            'json'
        );

    });

    $('#subcounty_1').change(function(){
        var subcountyid = $(this).val();
        if (subcountyid == '0' || subcountyid == '')
            return;
        $('#sms_facility').empty();
        $('#sms_facility').append("<option value='' selected='selected'>Select Health Facility</option>");
        $.get(
            '/api/v1/loc_facilities/' + subcountyid,
            {},
            function(data){
                var facilities = data;
                for(var i in facilities){
                    val = facilities[i]['id'];
                    txt = facilities[i]['name'];
                    $('#sms_facility').append(
                            $(document.createElement("option")).attr("value",val).text(txt)
                    );
                }
            },
            'json'
        );
	});
    /*

    $('#sendsms_2').click(function(){
        return false;
        $('#modal_res2').css({'color': 'green'});
        facilityid = $('#facilityid').val()
        msg = $('#msg').val()
        role = $('#role').val()
        $.post(
            '/api/v1/facilitysms/' + facilityid,
            {sms:msg, role:role},
            function(data){
            $('#modal_res2').html(data);
        });
        return false;
    });
    */
});

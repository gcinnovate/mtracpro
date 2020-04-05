$(function(){
    $('#district').change(function(){
        var districtid = $(this).val();
        if (districtid == '0' || districtid == "")
            return;
        $('#location').val(districtid);
        $('#facility').empty();
        $('#facility').append("<option value='' selected='selected'>Select Health Facility</option>");
		$.get(
            '/api/v1/loc_children/' + districtid,
            {xtype:'district', xid: districtid},
            function(data){
                var subcounties = data;
                for(var i in subcounties){
                    val = subcounties[i]["id"];
                    txt = subcounties[i]["name"];
                    $('#subcounty').append(
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
                    if($('#facility_x').val() == val){
                        $('#facility').append(
                            /*
                            $(document.createElement("option")).attr("value",val).text(txt)
                            */
                            "<option value='" + val + "' selected='selected'>" + txt + "</option>"
                        )
                    } else {
                         $('#facility').append(
                            "<option value='" + val + "'>" + txt + "</option>"
                        )
                    }
                }
            },
            'json'
        );
        // $('#facility').val($('#facility_x').val());
    });
});

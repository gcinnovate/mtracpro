$(function(){
	$('.report_edit_btn').click(function(event){
        event.preventDefault();
        $('#modal_res2').css({'color': 'green'});
        $('#modal_res2').addClass('alert');
        $('#modal_res2').addClass('alert-success');
        request_id = $('#request_id').val();
        $.post(
            '/api/v1/editreport/' + request_id,
            $('#report_form').serializeArray(),
            function(data){
                $('#modal_res2').html(data);
            });
        return false;
    });
});

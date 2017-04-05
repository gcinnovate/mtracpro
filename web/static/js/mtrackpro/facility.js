$(function(){
	$('.completeness_btn').click(function(){
        id_val = $(this).attr('id');
        $.get(
            '/api/v1/reportsthisweek/' + id_val,
            {},
            function(data){
                $('#modal_res4').html(data);
            });
    });
});

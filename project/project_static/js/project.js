$(document).ready(function(){

    $("body").bind("click", function (e) {
        $('.dropdown-toggle, .menu').parent("li").removeClass("open");
    });
    $(".dropdown-toggle, .menu").click(function (e) {
        var $li = $(this).parent("li").toggleClass('open');
        return false;
    });
    $('.alert-message .close').click(function(e) {
        $(this).parent().hide()
        e.preventDefault();
    });

});

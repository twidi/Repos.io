$(document).ready(function() {
    $.fn.popover.defaults = $.extend($.fn.popover.defaults, {
        html: true,
        title: 'data-popover-title',
        content: function() {
            return $(this).children('div').html();
        }
    });
    $('.rel_popover').popover({
        offset: 10
    });
});

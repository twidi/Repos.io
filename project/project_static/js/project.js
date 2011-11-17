$(document).ready(function() {
    $.fn.popover.defaults = $.extend($.fn.popover.defaults, {
        html: true,
        title: 'data-popover-title',
        content: function() {
            return $(this).children('div').html();
        },
        offset: 10
    });
    $('.rel_popover').popover();
    $('.rel_popover_left').popover({
        placement: 'left'
    });

    var extra_editor = $('#extra-editor');
    if (extra_editor.length) {
        // Ajaxify post for the extra editor

        var actions = {
            '/private/notes/delete/': 'Deleting note',
            '/private/notes/save/': 'Saving note',
            '/private/tags/delete/': 'Deleting tags',
            '/private/tags/save/': 'Saving tags',
        };

        var overlay = $('<div id="extra-ajax-overlay" />');
        extra_editor.append(overlay);

        function close_editor() {
            extra_editor.animate({
                opacity: 0
            }, 'fast', function() {
                $(this).hide();
            });
        } // close

        function show_overlay() {
            overlay.show().animate({
                opacity: 0.5
            }, 'fast', function() {
                $(this).addClass('displayed');
            });
        } // show_overlay

        function hide_overlay() {
            overlay.stop().removeClass('displayed').fadeOut('fast', function() {
                $(this).hide();
            });
        } // hide_overlay

        function ask_note_changed() {
            return window.confirm("Your note was changed but not saved. Continue and lose note's changes ?");
        } // ask_note_changed

        // manage submit of forms
        extra_editor.delegate('form', 'submit', function(ev) {
            var form = $(this);

            // if an allowed action ?
            var post_url = form.attr('action');
            if (!actions[post_url]) {
                return true;
            }

            // check if the new tag to create is not empty
            if (post_url == '/private/tags/save/' && form.find('input[name=act]').val() == 'create') {
                if (!form.find('input[name=tag]').val().trim()) {
                    var span = form.find('.error');
                    if (!span.length) {
                        span = $('<span />').addClass('error').text('You must add a tag...');
                        form.append(span);
                    }
                    span.stop().show().delay(1000).fadeOut(400);
                    return false;
                }
            }

            // display the ovjerlay
            overlay.text(actions[post_url]+'…');
            show_overlay();

            // check if note changed when submitting a tag form
            if (post_url.indexOf('/private/notes/') != 0 && extra_editor.find('#note-save-form #id_content').data('changed')) {
                if (!ask_note_changed()) {
                    hide_overlay();
                    return false;
                }
            }

            // simple post of the query
            $.ajax({
                type: 'POST',
                url: post_url,
                data: form.serialize(),
                context: extra_editor,
                dataType: 'text html'
            }) // base ajax

            // action on success
            .success(function(data, text_status, xhr) {
                // parse html
                var j_data = $(data);
                // find interesting parts
                var new_body = j_data.find('.modal-body');
                var new_messages = j_data.find('ul.messages');
                if (!new_body.length) {
                    // action if we want to close
                    close_editor();
                    var messages = $('#container > .messages');
                    if (messages.length) {
                        messages.replaceWith(new_messages);
                    } else {
                        $('#container').prepend(new_messages);
                    }
                } else {
                    // action if we stay in the window
                    new_body.prepend(new_messages);
                    extra_editor.find('.modal-body').replaceWith(new_body);
                }
            }) // success

            .error(function(xhr, text_status) {
                alert("We couldn't save your data : " + text_status);
            }) // error

            .complete(function() {
                hide_overlay();
            }); // complete

            return false;
        }); // form submit

        // save when note changed
        extra_editor.delegate('#note-save-form #id_content', 'change', function() {
            $(this).data('changed', true);
        });

        // manage note save buttons
        extra_editor.delegate('#note-save-form input[type=submit]', 'click', function() {
            var button = $(this),
                form = button.parents('form'),
                hidden = form.find('input[type=hidden][name=submit-close]');
            if (button.attr('name') == 'submit-close') {
                if (!hidden.length) {
                    hidden = $('<input />').attr('type', 'hidden').attr('name', 'submit-close').attr('value', button.val());
                    form.append(hidden);
                }
            } else if (hidden.length) {
                hidden.remove();
            }
        }); // note-save-form click;

        // manage close buttons
        extra_editor.find('.close, .modal-footer .btn').click(function() {
            if (extra_editor.find('#note-save-form #id_content').data('changed')) {
                if (!ask_note_changed()) {
                    hide_overlay();
                    return false;
                }
            }
            close_editor();
            return false;
        });

    } // if extra_editor
});

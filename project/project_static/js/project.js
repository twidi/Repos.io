/* Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license */

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

    function manage_extra_popover(dom) {
        dom.popover({
            placement: 'left'
        });
    }
    manage_extra_popover($('.rel_popover_extra'));

    var body_overlay = $('<div />').attr('id', 'boverlay'),
        extra_editor = $('#extra-editor');

    $('body').append(body_overlay);

    function show_body_overlay(cursor) {
        body_overlay.css('cursor', cursor);
        if (!body_overlay.is(':visible')) {
            body_overlay.fadeIn('fast');
        }
    } // show_body_overlay

    function hide_body_overlay() {
        body_overlay.fadeOut('fast');
    } // hide_body_overlay

    function show_editor() {
        if (!extra_editor.is(':visible')) {
            show_body_overlay('not-allowed');
            extra_editor.fadeIn('fast');
            extra_editor.data('changed', false);
        }
    } // show_editor

    function close_editor(need_update) {
        if (need_update && extra_editor.data('changed')) {
            var object_key = extra_editor.data('object-key'),
                url = '/private/close-ajax/' + object_key + '/';
            if (extra_editor.data('is-main')) {
                url += '?main=1';
            } else {
                var exclude = extra_editor.data('opener').parents('table.with_extras').data('private-exclude');
                if (exclude) {
                    url += '?exclude=' + exclude;
                }
            }
            $.get(url).success(function(data) {
                update_editor_opener($(data));
            });
        }
        hide_body_overlay();
        extra_editor.fadeOut('fast');
        extra_editor.data('object-key', null);
    } // close

    function update_editor_opener(new_dom) {
        var opener = extra_editor.data('opener');
        if (opener && new_dom && new_dom.length) {
            var new_dom_opener,
                is_main = extra_editor.data('is-main');
            if (is_main) {
                new_dom_opener = new_dom.find('#private');
            } else {
                new_dom_opener = new_dom.find('td.full, td.empty');
                if (new_dom_opener.length) {
                    opener.removeClass('full empty').addClass(new_dom_opener.get(0).className);
                }
            }
            if (new_dom_opener && new_dom_opener.length) {
                opener.empty().append(new_dom_opener.children());
            }
            if (!is_main) {
                manage_extra_popover(opener.find('.rel_popover_extra'));
                var page = $('body').attr('id');
                if (page == 'dashboard-tags') {
                    var td_tags = opener.prev();
                    var opener_tags = opener.find('ul.tags');
                    td_tags.empty().append(opener_tags.clone());
                } else if (page == 'dashboard-notes') {
                    opener.prev().text('Just now');
                }
            }
        }
    } // update_editor_opener

    function update_editor(new_dom) {
        var new_messages = new_dom.find('ul.messages'),
            close = false,
            new_body;

        if (extra_editor.length) {
            new_body = new_dom.find('.modal-body');
            if (new_body.length) {
                extra_editor.find('.modal-body').replaceWith(new_body);
                var new_object_link = new_dom.find('.modal-header h3 a');
                extra_editor.find('.modal-header h3 a').replaceWith(new_object_link);
            } else {
                close = true;
            }
        } else {
            var new_extra_editor = new_dom.find('#extra-editor');
            if (new_extra_editor.length) {
                $('#content').prepend(new_extra_editor);
                extra_editor = $('#extra-editor');
                new_body = extra_editor.find('.modal-body');
                ajaxify_extra_editor();
            }
        }

        if (close) {
            if (extra_editor.data('changed')) {
                update_editor_opener(new_dom);
            }
            close_editor(false);


            if (new_messages.length) {
                var messages = $('#container > .messages');
                if (messages.length) {
                    messages.replaceWith(new_messages);
                } else {
                    $('#container').prepend(new_messages);
                }
            }
        } else {
            new_body.prepend(new_messages);
            show_editor();
        }
    } // update_editor

    function ajaxify_extra_editor() {
        // Ajaxify post for the extra editor

        var actions = {
                '/private/notes/delete/': 'Deleting note',
                '/private/notes/save/': 'Saving note',
                '/private/tags/delete/': 'Deleting tags',
                '/private/tags/save/': 'Saving tags'
            },
            overlay = $('<div id="extra-ajax-overlay" />');

        extra_editor.addClass('ajaxified').append(overlay);

        function show_overlay() {
            overlay.fadeIn('fast');
        } // show_overlay

        function hide_overlay() {
            overlay.fadeOut('fast');
        } // hide_overlay

        function ask_note_changed() {
            return window.confirm("Your note was changed but not saved. Continue and lose changes ?");
        } // ask_note_changed

        // manage submit of forms
        extra_editor.delegate('form', 'submit', function(ev) {
            var form = $(this),
                post_url = form.attr('action');

            // if an allowed action ?
            if (!actions[post_url]) {
                return true;
            }

            // check if the new tag to create is not empty
            if (post_url === '/private/tags/save/' && form.find('input[name=act]').val() === 'create') {
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
            if (post_url.indexOf('/private/notes/') !== 0 && extra_editor.find('#note-save-form #id_content').data('changed')) {
                if (!ask_note_changed()) {
                    hide_overlay();
                    return false;
                }
            }

            // if we edit extra for the page's main object
            if (extra_editor.data('is-main')) {
                post_url += '?main=1';
            } else {
                var exclude = extra_editor.data('opener').parents('table.with_extras').data('private-exclude');
                if (exclude) {
                    post_url += '?exclude=' + exclude;
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
                extra_editor.data('changed', true);
                update_editor($(data));
            }) // success

            .error(function(xhr, text_status) {
                window.alert("We couldn't save your data : " + text_status);
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
            if (button.attr('name') === 'submit-close') {
                if (!hidden.length) {
                    hidden = $('<input />').attr('type', 'hidden').attr('name', 'submit-close').attr('value', button.val());
                    form.append(hidden);
                }
            } else if (hidden.length) {
                hidden.remove();
            }
        }); // note-save-form click;

        // manage links and close buttons
        extra_editor.find('a').click(function() {
            if (extra_editor.find('#note-save-form #id_content').data('changed')) {
                if (!ask_note_changed()) {
                    hide_overlay();
                    return false;
                }
            }
            if ($(this).is('.close, .btn')) {
                close_editor(true);
                return false;
            }
        });

        // click on rest of the page
        body_overlay.click(function() {
            $('#extra-editor')
                .animate({borderColor: 'rgba(255, 0, 0, 1)'}, 'fast')
                .delay(500)
                .animate({borderColor: 'rgba(0, 0, 0, 0.3)'}, 'fast');
        });

    } // ajaxify_extra_editor

    // click on links to open the editor
    var re_edit_extra = /[\?&]edit_extra=((?:core\.)?(?:account|repository):\d+)(?:&|\s+|$)/,
        current_object_key = $('#private').data('object-key');

    $('#private, table.with_extras td:last-child').delegate('a[href*="edit_extra="]', 'click', function() {
        var link = $(this),
            href = link.attr('href');
        if (!href) { return; }
        var match = href.match(re_edit_extra);
        if (!match) { return; }

        show_body_overlay('wait');

        var object_key = match[1],
            url = '/private/edit-ajax/' + object_key + '/';

        var opener = link.parent().parent('td[data-object-key="'+object_key+'"]'),
            is_main = false;
        if (!opener.length) {
            opener = link.parents('#private');
            is_main = true;
        }

        $.get(url)
        .success(function(data, text_status, xhr) {
            update_editor($(data));
            extra_editor.data('object-key', object_key);
            extra_editor.data('opener', opener);
            extra_editor.data('is-main', is_main);
        })
        .error(function(xhr, text_status) {
            window.location.href = href;
        });
        return false;
    });

    // manage the exta_editor if exists (not loaded via ajax)
    if (extra_editor.length) {
        ajaxify_extra_editor();
        var is_main = (edit_object_key === current_object_key),
            opener = is_main ? $('#private') : $('td[data-object-key='+edit_object_key+']');
        extra_editor.data('object-key', edit_object_key);
        extra_editor.data('opener', opener);
        extra_editor.data('is-main', is_main);
        show_editor();
    }
});

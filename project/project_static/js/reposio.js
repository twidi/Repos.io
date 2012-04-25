/* Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license */

$(document).ready(function() {

    window.Reposio = window.Reposio || {};

    var AjaxCache = {
        /* Make an ajax call and store the result in cache.
         * If the url is already cached, use the cached value
         */

        /* private fields/methods */
        _keys_to_hashes: {},
        _hashes_to_data: {},
        _hash: function(data) {
            return crc32(data);
        },
        _has_hash: function(hash) {
            return (hash in AjaxCache._hashes_to_data);
        },
        _get_by_hash: function(hash) {
            return AjaxCache._hashes_to_data[hash];
        },
        _set_by_hash: function(hash, data) {
            AjaxCache._hashes_to_data[hash] = data;
        },
        _get_hash: function(key) {
            return AjaxCache._keys_to_hashes[key];
        },
        _set_hash: function(key, hash) {
            AjaxCache._keys_to_hashes[key] = hash;
        },
        /* end of private fields/methods */

        key: function(url, querystring) {
            return Page.compute_url(url, querystring);
        },
        has: function(key) {
            return (key in AjaxCache._keys_to_hashes);
        },
        set: function(key, data) {
            // data = data.replace(/\s+/g, " "); // can't use this because of <pre> in readmes
            if (data instanceof $) {
                data = Node.outer_html(data);
            }
            data = data.trim();
            var hash = AjaxCache._hash(data);
            if (!AjaxCache._has_hash(hash)) {
                AjaxCache._set_by_hash(hash, data);
            }
            AjaxCache._set_hash(key, hash);
        },
        copy: function(key_from, key_to) {
            var hash = AjaxCache._get_hash(key_from);
            AjaxCache._set_hash(key_to, hash);
        },
        get: function(key) {
            var hash = AjaxCache._get_hash(key);
            return AjaxCache._get_by_hash(hash);
        },
        clear: function(keep_static) {
            if (keep_static) {
                var keys_to_delete = {};
                for(url in AjaxCache._keys_to_hashes) {
                    if (url.substr(url.length-8) == '/readme/') {
                        continue;
                    }
                    keys_to_delete[url] = AjaxCache._keys_to_hashes[url];
                }
                for (key in keys_to_delete) {
                    var hash = keys_to_delete[key];
                    delete AjaxCache._keys_to_hashes[key];
                    delete AjaxCache._hashes_to_data[hash];
                }
            } else {
                AjaxCache._keys_to_hashes = {};
                AjaxCache._hashes_to_data = {};
            }
        },
        ajax: function(url, querystring, callback) {
            var cache_key = AjaxCache.key(url, querystring);
            var callback_params = {
                url: url,
                querystring: querystring,
                cache_key: cache_key
            };
            if (AjaxCache.has(cache_key)) {
                callback_params.from_cache = true;
                callback(AjaxCache.get(cache_key), callback_params);
            } else {
                callback_params.from_cache = false;
                // we had ajax=1 to the querystring to avoid the browser cache the base url with partial content
                var aj = 'ajax=1';
                if (url.indexOf(aj) == -1 && (!querystring || querystring.indexOf(aj) == -1)) {
                    if (querystring) {
                        querystring += '&' + aj;
                    } else {
                        querystring = aj;
                    }
                }
                $.get(url, querystring, function(data) {
                    AjaxCache.set(cache_key, data);
                    callback(data, callback_params);
                });
            }
        }
    }; // AjaxCache


    var Node = {

        scroll_to: function($node, to_top) {
            if (!$node || !$node.length) { return; }
            $node = $node.eq(0);
            var node_top = $node.offset().top - 20,
                node_height = $node.outerHeight(),
                scroll_top = Page.html.scrollTop(),
                win_height = Page.win.height();
            if (scroll_top > node_top || scroll_top + win_height < node_top + node_height) {
                var new_top;
                if (to_top) {
                    new_top = node_top;
                } else {
                    new_top = node_top - win_height + node_height;
                    if (new_top > node_top) { new_top = node_top; }
                }
                Page.html.scrollTop(new_top);
            }
        },

        outer_html: function($node) {
            $node = $node.eq(0);
            var $clone = $('<div/>').append($node.clone()),
                result = $clone.html();
            delete $clone;
            return result;
        },

    _void: null}; // Node


    var Page = {
        win: $(window),
        doc: $(document),
        html: $('html'),
        body: $('body'),
        $node: $('body > section'),
        $overlay: $('#overlay'),
        section: '',
        subsection: '',
        title: '',
        url: document.location.pathname,
        history: window.History,
        base_url : document.location.protocol + '//' + document.location.host,
        _last_history_url: '',
        classes: {},
        _scroll: {
            margin: 200,
            section: $("body > section"),
            working: false
        },

        init: function() {
            Page.section = Reposio.section;
            Page.subsection = Reposio.subsection;
            Page.title = Page.doc.find('head').children('title').text();
            Page.body.addClass('js');
            Page.classes = { Article: Article, Section: Section, MainSearch: MainSearch };

            Page._init_alerts();
            Page.show_welcome();

            MainSearch.__init__();
            TagManager.__init__();
            Article.__init__();
            Section.__init__();
            Page._manage_events();
        },

        _manage_events: function() {
            Page._manage_input_clear(Page.html);

            Page.doc.delegate('.input-clear', 'click', function(ev) {
                $(this).parent().children('input[type=text]').val('').focus();
            });

            Page.history.Adapter.bind(window, 'statechange', function() {
                var state = Page.history.getState();
                if (state.url == Page.base_url + Page._last_history_url) { return; }
                if (state.data.url == Page._last_history_url) { return; }
                result = Page._load_items_from_history(state.data.args, Page);
                if (result !== false) { document.location.reload(); }
                return result;
            });

            Page.doc.delegate("a.endless_more", "click", function(ev) {
                return Page._on_more_click(this, ev);
            });

            Page.doc.delegate('.show_search_options', 'click', function(ev) {
                $(this).parents('.search').addClass('opened');
                return false;
            });

            $('#welcome span.close').click(Page.hide_welcome);

            Page.doc.delegate('#login-link a', 'click', Page.ask_for_login);
            Page.doc.delegate('#logout-link a', 'click', Page.ask_for_logout);

            Page.win.scroll(Page._on_window_scroll);

        },

        _load_items_from_history: function(state_data, parent) {
            if (!state_data || !state_data.length) { return ; }

            var step = state_data.shift(),
                klass = Page.classes[step.shift()],
                args = step;

            args.push(parent);
            args.push(state_data);

            return klass._load_from_history.apply(null, args);
        },

        _set_last_history_url: function(url) {
            Page._last_history_url = url;
        },

        get_article_container: function() {
            return this.$node;
        },

        _update_history: function(state_data, title, url, replace_current) {
            if (url == Page._last_history_url) { return; }
            Page._set_last_history_url(url);
            title += ' - Repos.io';
            var state = {
                args: state_data,
                url: url
            };
            if (replace_current) {
                Page.history.replaceState(state, title, url);
            } else {
                Page.history.pushState(state, title, url);
            }
        },

        _manage_input_clear: function($node) {
            if (!$node) { return; }
            $node.find('.search > form > fieldset.search_main > input[type=text]').each(function(index) {
                var $fieldset = $(this).parent();
                if ($fieldset.hasClass('with-input-clear')) { return; }
                $fieldset.addClass('with-input-clear');
                var $clear = $('<span/>').addClass('input-clear').text('x').attr('title', 'Clear input');
                $fieldset.append($clear);
            });
        },

        compute_url: function(url, querystring) {
            var result = url;
            if (querystring) {
                var sep = url.indexOf('?') == -1 ? '?' : '&';
                result += sep + querystring;
            }
            return result
        },

        set_title: function(title) {
            title += ' - Repos.io';
            document.title = title;
        },

        _on_more_click: function(node, ev) {
            var link = $(node),
                container = link.closest(".endless_container"),
                loading = container.find(".endless_loading"),
                querystring = "querystring_key=" + link.attr("rel").split(" ")[0],
                href = link.attr("href"),
                page = /page=(\d+)/.exec(href)[1];
            link.hide();
            loading.show();
            AjaxCache.ajax(href, querystring, function(data, ajax_params) {
                var parent = container.parent();
                container.before(data);
                container.remove();
                parent.trigger('page_loaded', [page]);
            });
            return false;
        },

        _on_window_scroll: function() {
            if (Page._scroll.working) { return; }
            Page._scroll.working = true;
            if (Page.doc.height() - Page.win.height() - Page.win.scrollTop() <= Page._scroll.margin) {
                Page._scroll.section.find("section.results:not(.with-opened), article.content:not(.with-opened) > section.details > section.current > section.results")
                .find("> nav a.endless_more:visible").click();
            }
            Page._scroll.working = false;
        },

        error: function(message, login_required) {
            if (!message || message.length > 200) {
                message = "An error occurred, preventing us to accomplish you request :(";
            }
            Page.message(message, true);
            if (login_required) {
                Page.ask_for_login();
            }
        },

        message: function(message, is_error, options) {
            var base_options = {
                //sticky: true,
                theme: is_error ? 'error' : 'success'
            };
            if (options) {
                $.extend(base_options, options);
            }
            $.jGrowl(message, base_options);
        },

        _init_alerts: function() {
            $.jGrowl.defaults.closerTemplate = 'Close all';
            $.jGrowl.defaults.speed = 'fast';
            $.jGrowl.defaults.afterOpen = function(element) {
                element.fadeTo(150, 1);
            };
        },

        ask_for_login: function() {
            Reposio.UserTags = null;
            Page.open_iframe(Reposio.urls.login + '?iframe=1');
            return false;
        },

        ask_for_logout: function() {
            Reposio.UserTags = null;
            Page.open_iframe(Reposio.urls.logout + '?iframe=1');
            return false;
        },

        on_logged: function(data) {
            Page.close_iframe();
            Reposio.Token = data.Token;
            Reposio.UserTags = data.UserTags;
            Page.message("You are now logged in !<br />If you've tried an action before, please do it again now.");
            $('#login-link').remove();
            var $header_links = $('#header-links'),
                $logout_link = $('<li />').attr('id', 'logout-link').append(
                    $('<a />').attr('href', Reposio.urls.logout).text('Logout')
                ),
                $user_link = $('<li />').attr('id', 'user-link').append(
                    $('<a />').attr('href', Reposio.urls.manage).text(
                        'Your account' + (data.nb_accounts > 1 ? 's' : '') + ' ( '
                    ).append(
                        $('<em />').text(data.username)
                    ).append(
                        (data.nb_accounts > 1 ? '...' : '') + ' ) '
                    )
                );
            $header_links.prepend($user_link, ' ', $logout_link);
        },

        on_not_logged: function() {
            Page.close_iframe();
            Page.error('We were unable to log you in :(');
        },

        on_logged_out: function() {
            Page.close_iframe();
            Reposio.UserTags = null;
            Page.message('You are now logged out !');
            $('#user-link').remove();
            $('#logout-link').remove();
            var $header_links = $('#header-links'),
                $login_link = $('<li />').attr('id', 'login-link').append(
                    $('<a />').attr('href', Reposio.urls.login).text('Login/Register')
                );
            $header_links.prepend($login_link);

        },

        on_not_logged_out: function() {
            Page.close_iframe();
            Page.error('We were unable to log you out :(');
        },

        open_iframe: function(url) {
            Page.close_iframe();
            var container = $('<div />').attr('id', 'iframe_container'),
                closer = $('<span />').addClass('close').text('X'),
                iframe = $('<iframe id="iframe_content" allowTransparency="true" scrolling="no" frameborder="0" />').attr('src', url);
            container.append(closer);
            container.append(iframe);
            Page.$overlay.show();
            Page.body.append(container);
            iframe.iframeAutoHeight({
                minHeight: 240,
                callback: function(callbackObject) {
                    iframe.unbind('load');
                }
            });
            closer.click(Page.close_iframe);
        },

        close_iframe: function() {
            $('#iframe_container').remove();
            Page.$overlay.hide();
        },

        show_welcome: function() {
            var $welcome = $('#welcome');
            if (!$welcome.length) { return; }
            if (Cookies.get('hide_welcome')) {
                $welcome.hide();
            } else if (Cookies.test()) {
                $welcome.find('span.close').show();
            }
        },

        hide_welcome: function() {
            $('#welcome').hide();
            Cookies.set('hide_welcome', '1', { expiresAt: new Date(2020, 1, 1) });
            return false;
        },

    _void: null}; // Page


    var Content = Class.$extend({

        __init__: function() {
            this._title = null;
            this.$node = null;
            this.is_loading = null;
        },

        _compute_title: function() {
            this._title = '';
        },

        _set_node: function($node) {
            this.$node = $node ? $node.eq(0) : null;
        },

        get_title: function() {
            if (!this._title) {
                this._compute_title();
            }
            return this._title;
        },

        _add_to_history: function(querystring, replace_current) {
            var state_data = [];
            var current = this;
            while (current != Page) {
                state_data.push(current.get_state_data());
                current = current.get_parent();
            };
            var url = Page.compute_url(this.url, querystring);
            Page._update_history(state_data.reverse(), this.get_title(), url, replace_current);
        },

        _get_loading_parent_node: function() {
            return this.$node;
        },

        _get_loading_node: function() {
            var $loading_parent_node = this._get_loading_parent_node();
            if (!$loading_parent_node) { return null; }
            var $loading = $loading_parent_node.children('.loading');
            if (!$loading.length) {
                $loading = $('<p/>').addClass('loading').text('Loading in progress...');
                if ($loading_parent_node.hasClass('results')) {
                    $loading_parent_node.prepend($loading);
                } else {
                    $loading_parent_node.append($loading);
                }
                $loading.after('<hr style="display: none" />');
            }
            return $loading;
        },

        _set_loading: function(is_loading) {
            this.is_loading = is_loading;
            var $loading = this._get_loading_node();
            if ($loading) {
                $loading.toggle(is_loading);
            }
        },

        _ajax: function(callback, querystring) {
            var that = this;
            AjaxCache.ajax(this.url, querystring, function(data, ajax_params) {
                $.proxy(callback, that)(data, ajax_params);
            });
        },

        get_with_openable_parent: function() {
            var parent = this.get_parent();
            if (!parent || !parent.get_with_openable_parent) {
                return null;
            } else if (parent.set_with_opened) {
                return parent;
            } else {
                return parent.get_with_openable_parent();
            }
        },

        get_with_opened_node: function() {
            return this.$node;
        },

        set_with_opened: function(toggle, manage_family) {
            var with_opened_node = this.get_with_opened_node();
            if (manage_family && !toggle) {
                with_opened_node.find('article.content.with-opened').each(function() {
                    var article = Article.get_by_node($(this));
                    article.set_with_opened(false, false);
                });
            }
            with_opened_node.toggleClass('with-opened', toggle);
            if (manage_family && toggle && this.set_parent_with_opened) {
                this.set_parent_with_opened(true);
            }
        },

    _void: null}); // Content


    var PageableContent = Content.$extend({

        __init__: function() {
            this.$super();
            _last_page = 1;
        },

        _set_last_page: function(page) {
            if (!page) { page = 1; }
            this._last_page = page;
            page = parseInt(page, 10);
            if (this.$node) {
                this.get_article_container().children('article.content:not([data-page])').attr('data-page', page);
            }
        },

    _void: null}); // PageableContent


    var TagManager = Class.$extend({
        __classvars__: {
            obj: null,
            supports_datalist: null,

            groups: {
                tags: 'Tags',
                places: 'Places',
                projects: 'Projects'
            },

            __init__: function() {
                TagManager.obj = TagManager();
                TagManager._manage_events();
            },

            _manage_events: function() {
                Page.doc.delegate('a.more-tags', 'click', function(ev) {
                    TagManager.obj._on_more_tags_click(this, ev);
                });
                Page.doc.mousedown(function(ev) {
                    if (TagManager.obj.opened) {
                        var $target = $(ev.target);
                        if (!$target.hasClass('more-tags') && !$target.parents('#tags-popin').length) {
                            TagManager.obj.close();
                        }
                    }
                });
            },


        _void: null}, // __classvars__

        __init__: function() {
            this.popin = null;
            this._stylesheet = null;
            this.article = null;
            this.opened = false;
            this.search_type = null;
        },

        _on_more_tags_click: function(link, ev) {
            var $link = $(link),
                article = Article.get_by_node($link);
            if (!article) { return; }

            // the click is also managed (via delegate) on the whole article
            // so we stop here all propagation
            ev.stopPropagation();
            ev.stopImmediatePropagation();
            ev.preventDefault();

            if (!Reposio.UserTags) {
                Page.error('You need to be logged for this', true);
                return false;
            }

            if ($link.hasClass('selected')) {
                this.close();
                return false;
            }

            this.open(article);

            return false;
        },

        _get_link: function(article) {
            return article.$node.find('> footer a.more-tags');
        },


        close: function() {
            if (this.popin) {
                this.popin.detach();
            }
            this.article = null;
            $('.more-tags').removeClass('selected loading');
            this.opened = false;
        },

        open: function(article) {
            this.close();
            this.article = article;
            var $link = this._get_link(article);
            $link.addClass('loading');
            this._prepare_popin(article);
            $link.removeClass('loading').addClass('selected');
            this.opened = true;
            $link.parent().children('.user-tags').addClass('opened');
        },

        _create_popin: function() {
            this.popin = $('#tags-popin');

            if (this.popin.length) {
                if (this.popin.hasClass('from-html')) {
                    this.popin.remove();
                    this.popin = null;
                } else {
                    return;
                }
            }

            var p = $('<div/>').attr('id', 'tags-popin'),
                lines = $('<ul/>');

            if (TagManager.supports_datalist === null) {
                TagManager.supports_datalist = (document.createElement('datalist') && !!window.HTMLDataListElement);
            }

            for (var group_code in TagManager.groups) {
                var group_name = TagManager.groups[group_code],
                    $line = $('<li/>')
                        .append($('<label/>')
                        .text(group_name))
                        .data('type', group_code)
                        .addClass('tags-type-' + group_code),
                    $list = $('<ul />').addClass('tags'),
                    $datalist = (TagManager.supports_datalist ? $('<datalist />').attr('id', 'datalist-' + group_code) : null);


                var add_tags = function(tags) {
                    for (tag_index in tags) {
                        var tag = tags[tag_index],
                            $li = $('<li/>')
                                    .text(tag.name)
                                    .data('slug', tag.slug)
                                    .append('<span />');
                        if (group_code == 'tags' && (tag.for_only || Reposio.UserTags.tags_for_only)) {
                            $li.addClass((tag.for_only || Reposio.UserTags.tags_for_only) + '_only');
                        }
                        $list.append($li);

                        if (TagManager.supports_datalist) {
                            $datalist.append($('<option/>')
                                        .attr('value', tag.name)
                                        .text(tag.name)
                                    );
                        }
                    }
                };

                add_tags(Reposio.UserTags[group_code]);

                var $input = $('<input />')
                    .attr('type', 'text')
                    .attr('name', 'tag')
                    .attr('placeholder', 'New ' + group_code.substr(0, group_code.length - 1));

                if (TagManager.supports_datalist) {
                    $input.attr('list', 'datalist-' + group_code)
                          .attr('autocomplete', 'off');
                }

                var $form = $('<form >')
                    .attr('method', 'post')
                    .append($input)
                    .append(
                        $('<input />')
                            .attr('type', 'submit')
                            .attr('name', 'submit')
                            .val('=')
                            .attr('title', 'Add')
                    );

                if (TagManager.supports_datalist) { $form.append($datalist); }

                $list.prepend($('<li />').addClass('add-form').append($form));

                lines.append($line.append($list));
            } // for group_code

            p.append(lines);
            this.popin = p;

            this.popin.delegate('form', 'submit', function(ev) {
                return TagManager.obj._on_add_form_submit(this, ev);
            });
            this.popin.click(function(ev) {
                return TagManager.obj._on_click(this, ev);
            });
        },

        _get_line_cache: {},
        _get_line: function(type) {
            if (!this._get_line_cache[type]) {
                this._get_line_cache[type] = this.popin.children('ul').children('li.tags-type-' + type);
            }
            return this._get_line_cache[type];
        },

        _find_tag_cache: {places:{}, projects: {}, tags: {}},
        _find_tag: function(type, slug) {
            var found = false;
            if (!this._find_tag_cache[type][slug]) {
                var $container = this._get_line(type);
                $container.find('li').each(function() {
                    var $tag = $(this);
                    if ($(this).data('slug') == slug) {
                        found = $tag;
                        return false;
                    }
                });
                if (found && !found.hasClass('official')) {
                    this._find_tag_cache[type][slug] = found;
                }
            } else {
                found = this._find_tag_cache[type][slug];
            }
            return found;
        },

        _add_tag: function(tag, selected, official, search_type) {
            var type = this._get_tag_type(tag.name),
                $line = this._get_line(type);
                $all = $line.find('li:not(.add-form)'),
                $li = $all.filter(function() {
                        return ($(this).data('slug') == tag.slug);
                    });

            if ($li.length) {
                if (search_type == 'people') {
                    $li.removeClass('repositories_only');
                } else {
                    $li.removeClass('people_only');
                }
            } else {

                $li = $('<li/>')
                        .text(tag.name)
                        .data('slug', tag.slug)
                        .append('<span />')
                        .addClass(search_type + '_only');

                if (TagManager.supports_datalist) {
                    var $datalist = $line.find('datalist');
                    $datalist.append($('<option/>')
                                .attr('value', tag.name)
                                .text(tag.name)
                            );
                    $datalist.children('option').tsort();
                }

                $line.children('ul')
                    .append($li)
                    .find('li')
                        .tsort(':not(.add-form)', {place: 'end'});

            }

            this._change_tag_status($li, selected ? 'selected' : '');
            if (official) { $li.addClass('official'); }
        },

        _prepare_popin: function(article) {
            var that = this;

            if (!this.popin) { this._create_popin(); }

            this.search_type = article.search_type;
            this.popin.removeClass('people repositories').addClass(this.search_type);

            // add article official tags
            this.popin.find('ul.tags li.official').remove();
            this.popin.find('ul.tags li.official-used').removeClass('official-used');
            var officials = article.$node.find('> footer ul.official-tags li');

            officials.each(function() {
                var $official = $(this),
                    tag = {name: $official.text(), slug: $official.data('slug') },
                    found = that._find_tag('tags', tag.slug);
                    if (found) {
                        found.addClass('official-used');
                        return;
                    }

                that._add_tag(tag, false, true, that.search_type);
            });

            // change selected/unselected tags
            var tags = this.popin.find('ul.tags li:not(.add-form)');
            tags.each(function() {
                that._change_tag_status($(this));
            });
            article.$node.find('> footer ul.user-tags li li').each(function() {
                var slug = $(this).data('slug');
                tags.each(function() {
                    var $label = $(this);
                    if ($label.data('slug') == slug) {
                        that._change_tag_status($label, 'selected');
                    }
                });
            });

            // hide and add it to the dom
            var $link = this._get_link(article);
            this.popin.css('visibility', 'hidden');
            $link.after(this.popin);

            // position to have the link at the center if possible
            var link_left = $link.position().left,
                popin_left = link_left - this.popin.width() / 2;

            if (popin_left < 0) { popin_left = 0; }
            var popin_width = this.popin.outerWidth();
            this.popin.css('left', popin_left);
            var new_popin_width = this.popin.outerWidth();
            if (new_popin_width < popin_width) {
                popin_left = popin_left - (popin_width - new_popin_width) - 1;
                this.popin.css('left', popin_left);
            }

            this._adjust_arrow($link);

            // finally, display
            Node.scroll_to(this.popin);
            this.popin.css('visibility', 'visible');

            // focus on new tag imput
            this._get_line('tags').find('input[type=text]').focus();
        },

        _adjust_arrow: function($link) {
            if (!$link || !$link.length) { return; }

            // position to have the link at the center if possible
            var link_left = $link.position().left,
                popin_left = this.popin.position().left,
                arrow_left = Math.min(Math.max(link_left - popin_left + 10, 13), this.popin.width()-15);
            if (this._stylesheet) { this._stylesheet.remove(); }
            this._stylesheet = $('<style type="text/css">#tags-popin:before { left: ' + arrow_left + 'px !important}</style>');
            this._stylesheet.appendTo('head');
            this.popin.toggleClass('left-arrow', (arrow_left < 75));

            // if big footer, adjut vertical position to be below the center
            var popin_top = '100%',
                link_height = $link.height();
            if ($link.parent().height() > link_height*1.2) {
                popin_top = Math.round($link.position().top + link_height);
                popin_top + popin_top + 'px';
            }
            this.popin.css('top', popin_top);
        },

        _on_add_form_submit: function(form, ev) {
            var $form = $(form),
                tag = { name: $form.children('input[type=text]').val().trim() },
                $li = $form.parent(),
                type = $li.parents('li').data('type');

            if (!tag.name) { return false; }

            var first  = tag.name.substr(0, 1);
            if (type == 'places') {
                if (first != '@') { tag.name = '@' + tag.name; }
            } else if (type == 'projects') {
                if (first != '#') { tag.name = '#' + tag.name; }
            }

            if (type != 'tags' && tag.name.length <= 1) {
                return false;
            }

            return this._post($li, tag, true, true);
        },

        _on_click: function(popin, ev) {
            var $li = $(ev.target).closest('ul.tags li');
            if (!$li.length) { return false; }
            if ($li.hasClass('loading')) { return false; }
            if ($li.hasClass('add-form')) {
                if (ev.target.tagName.toLowerCase() == 'input' && ev.target.type == 'submit') {
                    $(ev.target).closest('form').submit();
                }
                return false;
            }
            $li.removeClass('official');

            var add = !$li.hasClass('selected');
            this._change_tag_status($li, 'loading' + (add ? 'selected' : ''));

            var tag = {
                    name: $li.contents().eq(0).text(),
                    slug: $li.data('slug')
                };

            return this._post($li, tag, add, false);
        },

        _post: function($li, tag, add, is_new) {
            var $link = this._get_link(this.article),
                post_data = {
                    tag: tag.name,
                    content_type: $link.data('content-type'),
                    object_id: $link.data('object-id'),
                    act:  is_new ? 'create' : (add ? 'add' : 'remove'),
                    csrfmiddlewaretoken: Reposio.Token
                },
                current_article = this.article,
                that = this,
                is_now_set = false;

            $.post('/private/tag/save/', post_data)
                .success(function(data) {
                    if (data.error) {
                        Page.error(data.error, data.login_required);
                    } else {
                        is_now_set = data.is_set;
                        that._on_post_success(current_article, tag, is_new, data);
                    }
                })
                .error(function(xhr) {
                    is_now_set = false;
                    Page.error(xhr.responseText);
                })
                .complete(function() {
                    if (that.popin.is(':visible') && !is_new && that.article == current_article) {
                        that._change_tag_status($li, is_now_set ? 'selected' : '');
                    }
                });

            return false;
        },

        _on_post_success: function(article, tag, is_new, data) {
            AjaxCache.clear(true);
            Page.message(data.message);
            tag.name = tag.name.toLowerCase();
            if (is_new) {
                tag.slug = data.slug;
                this._add_tag(tag, true, false, article.search_type);
                var $line = this._get_line(this._get_tag_type(tag.name));
                $line.find('input[type=text]').val('');
            }
            this._update_article(article, data.is_set, tag, article.search_type);
            this._update_main_search(data.is_set, tag, article.search_type);
            if (this.popin.is(':visible') && this.article == article) {
                this._adjust_arrow(this.popin.prev('a.more-tags'));
            }
        },

        _change_tag_status: function($label, status) {
            if (!status) { status = ''; }
            var $span = $label.children('span'),
                span_char = '';
            if (status.indexOf('selected') != -1) {
                span_char = '_';
                $label.addClass('selected');
            } else {
                span_char = '=';
                $label.removeClass('selected');
            }
            if (status.indexOf('loading') != -1) {
                span_char = '[';
                $label.addClass('loading');
            } else {
                $label.removeClass('loading');
            }
            $span.text(span_char);
        },

        _update_main_search: function(add, tag, search_type) {
            if (MainSearch.obj && MainSearch.obj.is_active && add) {
                MainSearch.obj._add_tag(tag, search_type);
            }
        },

        _update_article: function(article, add, tag, search_type) {
            var type = this._get_tag_type(tag.name);

            article.run_for_all_nodes(function() {
                var $node = $(this),
                    $footer = $node.children('footer'),
                    $main_container = $footer.children('ul.user-tags'),
                    $type_container = $(),
                    $tag_container = $(),
                    attach_main = attach_type = attach_tag = false;

                if (!$main_container.length) {
                    if (!add) { return; }
                    attach_main = true;
                    $main_container = $('<ul/>').addClass('tags user-tags opened');
                } else {
                    $type_container = $main_container.children('li.tags-type-' + type);
                }

                if (!$type_container.length) {

                    if (!add) { return; }
                    attach_type = true;
                    var $ul = $('<ul />');
                    $ul.append($('<span/>').text('Your ' + TagManager.groups[type].toLowerCase()));
                    $type_container = $('<li/>')
                        .addClass('tags-type-' + type)
                        .append($ul);

                } else {

                    $tag_container = $type_container.children('ul').children('li').filter(function() {
                        return ($(this).data('slug') == tag.slug);
                    });

                }

                if ($tag_container.length && !add) {
                    $tag_container.remove();
                    if (!$type_container.children('ul').children('li').length) {
                        $type_container.remove();
                    }
                    if (!$main_container.children('li').length) {
                        $main_container.remove();
                        $footer.children('a.show-user-tags').remove();
                        $footer.children('a.more-tags').removeClass('user-has-tags');
                    }

                    return;

                } else if (!$tag_container.length && add) {

                    attach_tag = true;
                    var url = '/?type=' + search_type + '&filter=tag:' + tag.slug;
                    $tag_container = $('<li />')
                        .data('slug', tag.slug)
                        .append($('<a/>').attr('href', url).text(tag.name));

                } else {
                    if (!add) { return; }
                }

                if (attach_tag) {
                    $type_container.children('ul')
                        .append($tag_container)
                        .children('li')
                            .tsort()

                }
                if (attach_type) {
                    $main_container
                        .append($type_container)
                        .children('li')
                            .tsort('> ul > span');
                }
                if (attach_main) {
                    var $official_tags = $footer.children('ul.tags'),
                        $link_show = $footer.children('a.show-user-tags');
                    if (!$link_show.length) {
                        $link_show = $('<a />').addClass('show-user-tags').text('Show your tags');
                    }
                    $official_tags.after($main_container);
                    $official_tags.after($link_show);
                    $footer.children('a.more-tags').addClass('user-has-tags');
                }

            });
        },

        _get_tag_type: function(tag_name) {
            var type = 'tags';
            if (tag_name) {
                var start = tag_name.charAt(0);
                if (start == '@') {
                    type = 'places';
                } else if (start == '#') {
                    type = 'projects';
                }
            }
            return type;
        },


    _void: null}); // TagManager


    var MainSearch = PageableContent.$extend({
        __classvars__: {
            obj: null,

            __init__: function() {
                MainSearch.obj = MainSearch();
                if (MainSearch.obj.is_active) {
                    MainSearch.obj._prepare_existing();
                    MainSearch._manage_events();
                }
            },

            _manage_events: function() {
                var $form = $('#main_search form');
                $form.submit(function(ev) {
                    return MainSearch.obj._on_submit(this, ev)
                })
                $form.delegate('button', 'click', function(ev) {
                    return MainSearch.obj._on_button_click(this, ev);
                });
                $('#show_filters').click(function(ev) {
                    return MainSearch.obj._on_show_filters_click(this, ev);
                });
                Page.doc.delegate('body > section > section.results', 'page_loaded', function(ev, page) {
                    MainSearch.obj._set_last_page(page);
                    return false;
                });
                Page.doc.delegate('body > section > section.results.with-opened > div.return', 'click', function(ev) {
                    return MainSearch.obj._on_return_to_list_click(this, ev);
                });
            },

            _load_from_history: function(querystring, parent, next_steps) {
                if (!MainSearch.obj.is_active) {
                    return Page._load_items_from_history(next_steps, parent);
                }
                Page._set_last_history_url(Page.compute_url(Page.url, querystring));
                return MainSearch.obj._load_from_history(querystring, next_steps);
            },

        _void: null}, // __classvars__

        __init__: function() {
            this.$super();

            this.url = Page.url;

            this.is_active = false;
            this.querystring = '';

            this._set_node($('#main_search'));
            if (!this.$node.length) {
                this._set_node(null);
                return;
            }

            this.is_active = true;
            this.$form = this.$node.children('form');
            this.$results = this.$node.parent().children('section.results');
        },

        _prepare_existing: function() {
            if (this.$results.find('article.content.with-details').length) { return; }
            var querystring = document.location.search.substr(1);
            this._unserialize_form(querystring);
            this.querystring = this.$form.serialize();
            var cache_key = AjaxCache.key(this.url, this.querystring);
            AjaxCache.set(cache_key, this.$results.html());
            if (!Page._last_history_url) {
                this._add_to_history(this.querystring, true);
            }
            Page.set_title(this.get_title());
            this._set_last_page(1);
        },

        _unserialize_form: function(querystring) {
            if (querystring.indexOf('q=') == -1) {
                querystring += '&q=';
            }
            this.$form.unserializeForm(querystring, { 'override-values': true });
            if (!this._get_type()) {
                $('#search_type_repositories').prop('checked', true);
            }
            var $search_filter = $('#search_filter'),
                $filter = $search_filter.find('input[name=filter]:checked');
            $search_filter.toggleClass('opened', !!$filter.val());
            if (!$filter.is(':visible')) {
                $('#search_filter_none').prop('checked', true);
            }
            if (!this.$form.children('fieldset.search_order').find('input[name=order]:checked:visible').length) {
                $('#search_order_none').prop('checked', true);
            }
        },

        _get_type: function() {
            return this.$form.find('input[name=type]:checked').val();
        },

        _on_submit: function(node, ev) {
            var $input_q = this.$form.find('input[name=q]'),
                $search_filter = $('#search_filter'),
                $input_filter = $search_filter.find('input[name=filter]:checked'),
                filter_val = $input_filter.val(),
                $order = this.$form.children('fieldset.search_order').find('input[name=order]:checked');

            $input_q.val($input_q.val().trim());

            $search_filter.toggleClass('opened', !!filter_val);

            if (!$input_filter.is(':visible')) {
                $('#search_filter_none').prop('checked', true);
            }
            if (!$order.is(':visible')) {
                $('#search_order_none').prop('checked', true);
            }

            if (!filter_val && !$input_q.val()) {
                this.$results.hide();
                return false;
            }

            this.querystring = this.$form.serialize();
            return this.load(null, this.querystring);
        },

        _on_button_click: function(node, ev) {
            var $button = $(node),
                name = $button.attr('name');
            if (name.indexOf('direct-') == 0) {
                // we select the matching radio, to have consistent querystring, for caching
                var real_name = name.substr(7),
                    value = $button.val();
                this.$form.find('input[name=' + real_name + '][value="' + value + '"]').prop('checked', true);
            }
            return this._on_submit(this.$form.get(0), ev);
        },

        load: function(callback, querystring) {
            if (!callback) { callback = this._on_results_loaded; }
            this._remove_results();
            this._set_last_page(1);
            this.$results.show();
            this._set_loading(true);
            this._ajax(callback, querystring);
            return false
        },

        _load_from_history: function(querystring, next_steps) {
            return this._load_from_querystring(querystring, function() {
                if (!next_steps.length) {
                    Page.set_title(this.get_title());
                }
                Page._load_items_from_history(next_steps, this);
            });
        },

        _load_from_querystring: function(querystring, callback) {
            this._unserialize_form(querystring);
            this.querystring = this.$form.serialize();
            this.load(function(results, ajax_params) {
                this._on_results_loaded(results, ajax_params);
                if (callback) {
                    $.proxy(callback, this)(results, ajax_params);
                }
            }, this.querystring);
            return false;
        },

        _add_to_history: function(querystring, replace_current) {
            if (!querystring) { querystring = this.querystring; }
            return this.$super(querystring, replace_current);
        },

        _on_results_loaded: function(results, ajax_params) {
            this._set_loading(false);
            if (results) {
                this.$results.append(results);
                this.$results.show();
            } else {
                this.$results.hide();
            }
            this._set_last_page(1);
            this._add_to_history(ajax_params.querystring);
        },

        _remove_results: function() {
            this.$results.children('article.content, nav, p.empty').remove();
            this.set_with_opened(false, false);
        },

        get_state_data: function() {
            return ['MainSearch', this.querystring];
        },

        get_parent: function() {
            return Page;
        },

        get_article_container: function() {
            return this.$results;
        },

        _get_loading_parent_node: function() {
            return this.$results;
        },

        get_title: function() {
            var title = '';


            // get the type
            var type = this.$form.children('input[name=type]:checked').val();
            var type_caps = type.substr(0, 1).toUpperCase() + type.substr(1);

            // add the filter
            var filter_title = '',
                $input_filter = $('#search_filter').find('input[name=filter]:checked'),
                filter_val = $input_filter.val();
            if (filter_val) {
                filter_title = $input_filter.next().text();
                var start = filter_title.substr(0, 1);
                if (start == '#') {
                    filter_title = type_caps + " for project `" + filter_title + "`";
                } else if (start == '@') {
                    filter_title = type_caps + " for place `" + filter_title + "`";
                } else if (filter_val == 'tag:starred') {
                    filter_title = 'Starred ' + type;
                } else if (filter_val == 'tag:check-later') {
                    filter_title = type_caps + ' to check later';
                } else if (filter_val.substr(0, 4) == 'tag:') {
                    filter_title = type_caps + " with tag `" + filter_title + "`";
                } else if (filter_val == 'noted') {
                    filter_title = 'Noted ' + type;
                } else {
                    filter_title = filter_title + ' ' + type;
                }
            }

            // add the search query
            var q = this.$form.find('input[name=q]').val();
            if (q) {
                if (filter_title) {
                    title = "Search for `" + q + "` in " + filter_title.substr(0, 1).toLowerCase() + filter_title.substr(1);
                } else {
                    title = "Search " + type + " for `" + q + "`";
                }
            } else {
                if (filter_title) {
                    title = filter_title;
                } else {
                    return 'Home';
                }
            }

            var final_parts = [];
            // add search options
            this.$form.find('fieldset.search_options input:checked').each(function() {
                final_parts.push($(this).next().text().replace(' ?', ''));
            });
            // add search order
            var $input_sort = this.$form.find('fieldset.search_order input[name=order]:checked');
            if ($input_sort.val()) {
                final_parts.push('Sort by ' + $input_sort.next().text());
            }
            // finalize
            if (final_parts.length) {
                title += ' (' + final_parts.join(', ') + ')'
            }
            return title;
        },

        _on_article_tag_click: function(node, ev) {
            var href = $(node).attr('href'),
                querystring = href.substr(href.indexOf('?')+1);
            return this._load_from_querystring(querystring);
        },

        _get_tags_line_cache: {},
        _get_tags_line: function(type) {
            if (!this._get_tags_line_cache[type]) {
                this._get_tags_line_cache[type] = this.$node.find('fieldset.tags-type-' + type);
            }
            return this._get_tags_line_cache[type];
        },

        _add_tag: function(tag, search_type) {
            if (!this.is_active) { return; }
            var type = TagManager.obj._get_tag_type(tag.name),
                $line = this._get_tags_line(type),
                $container = $(),
                attach_line = false;

            if (!$line.length) {
                attach_line = true;
                $line = $('<fieldset/>')
                            .addClass('tags-type-' + type)
                            .append($('<legend/>').text('Your ' + type))
                            .append('<ul/>');
                if (type == 'tags') {
                    $line.addClass(search_type + '_only');
                }
            } else {
                if (search_type == 'people') {
                    $line.removeClass('repositories_only');
                } else {
                    $line.removeClass('people_only');
                }
                $container = $line.children('ul').children('li:has(input[value="tag:' + tag.slug + '"])');
            }

            if (!$container.length) {
                $container = $('<li/>')
                    .addClass(search_type + '_only')
                    .append(
                        $('<input />')
                            .attr('id', 'search_filter_tag_' + tag.slug)
                            .attr('type', 'radio')
                            .attr('value', 'tag:' + tag.slug)
                            .attr('name', 'filter')
                    )
                    .append(
                        $('<label />')
                            .attr('for', 'search_filter_tag_' + tag.slug)
                            .attr('onclick', '')
                            .text(tag.name)
                    )
                    .append(
                        $('<button />')
                            .attr('value', 'tag:' + tag.slug)
                            .attr('name', 'direct-filter')
                            .attr('type', 'submit')
                            .text('$')
                    );

                $line.children('ul')
                    .append($container)
                    .children('li')
                        .tsort();
            } else {
                if (search_type == 'people') {
                    $container.removeClass('repositories_only');
                } else {
                    $container.removeClass('people_only');
                }
            }

            if (attach_line) {
                this.$node.find('fieldset.special-filters').before($line);
                this.$node.find('#search_filter fieldset').tsort(':has(legend)[class^=tags-type]', { place: 'first', attr: 'class' });
            }
        },

        _on_show_filters_click: function(link, ev) {
            $('#search_filter').addClass('opened');
            return false;
        },

        set_with_opened: function(toggle, manage_family) {
            if (toggle && !this.$results.children('div.return').length) {
                var div = $('<div />').addClass('return').text('Return to the list');
                this.$results.prepend(div);
            }
            this.$super(toggle, manage_family);
        },

        get_with_opened_node: function() {
            return this.$results;
        },

        _on_return_to_list_click: function(obj, ev) {
            this.get_article_container().children('article.content.with-details').each(function() {
                var article = Article.get_by_node($(this));
                article.close(true);
            });
            return false;
        },

    _void: null}); // MainSearch


    var Article = Content.$extend({

        __classvars__: {
            _by_url: {},

            _add_by_url: function(article) {
                Article._by_url[article.url] = article;
            },

            get_by_url: function(url) {
                if (url in Article._by_url) {
                    return Article._by_url[url];
                }
                return Article(url);
            },

            get_by_node: function($node) {
                var $article = $node.closest('article.content'),
                    url = $article.find('> header > h1 > a').attr('href'),
                    article = Article.get_by_url(url);
                article._set_node($article);
                return article;
            },

            __init__: function() {
                Article._manage_events();
                Article._prepare_existing();
            },

            _prepare_existing: function($node) {
                $('article.content:has(>section.details)', $node).each(function(index) {
                    var $article = $(this),
                        article = Article.get_by_node($article);
                    article._prepare_existing();
                });
            },

            _manage_events: function() {
                Page.doc.delegate('article.content > :not(section.details, footer), article.content > footer > section > ul.actions > li.action-more', 'click', function(ev) {
                    return Article._on_click(this, ev);
                });
                Page.doc.delegate('section.details > header', 'click', function(ev) {
                    return Article._on_details_header_click(this, ev);
                });
                if (MainSearch.obj.is_active) {
                    Page.doc.delegate('article.content > footer > .tags a', 'click', function(ev) {
                        return MainSearch.obj._on_article_tag_click(this, ev);
                    });
                }
                Page.doc.delegate('article.content > footer > section > ul.actions > li.action-star > form', 'submit', function(ev) {
                    return Article._on_toggle('star', this, ev);
                });
                Page.doc.delegate('article.content > footer > section > ul.actions > li.action-check > form', 'submit', function(ev) {
                    return Article._on_toggle('check', this, ev);
                });
                Page.doc.delegate('article.content > footer > a.show-user-tags', 'click', function(ev) {
                    return Article._on_show_user_tags_click(this, ev);
                });
                Page.doc.delegate('article.content > footer > section > ul.actions > li.action-note > a', 'click', function(ev) {
                    return Article._on_edit_note_click(this, ev);
                });
                Page.doc.delegate('article.content > footer > section > ul.actions > li.action-note > form > a', 'click', function(ev) {
                    return Article._on_cancel_note(this, ev);
                });
                Page.doc.delegate('article.content > footer > section > ul.actions > li.action-note > form > input[type=submit]', 'click', function(ev) {
                    return Article._on_note_form_input_click(this, ev);
                });
                Page.doc.delegate('article.content > footer > section > ul.actions > li.action-note > form', 'submit', function(ev) {
                    return Article._on_save_note(this, ev);
                });
                Page.doc.delegate('a.owner', 'click', function(ev) {
                    return Article._on_owner_click(this, ev);
                });
                Page.doc.delegate('a.parent-fork', 'click', function(ev) {
                    return Article._on_parent_fork_click(this, ev);
                });
            },

            _on_click: function(node, ev) {
                var article = Article.get_by_node($(node)),
                    tag = ev.target.tagName.toUpperCase(),
                    $target = $(ev.target);

                // if we click a link with a different url, do not handle it
                if (tag == 'A' && $target.attr('href') != article.url) {
                    return;
                }
                // idem with a form
                if (tag == 'BUTTON' || tag == 'FORM') {
                    var action = $target.closest('form').attr('action');
                    if (action != "" && action != article.url) {
                        return;
                    }
                }

                // do not handle this if the article is not in a results section
                if (!article.$node.hasClass('with-opened') && !article.$node.parent('section.results').length) {
                    return false;
                }

                return article._click();
            },

            _on_details_header_click: function(node, ev) {
                // only handle click on links
                var tag = ev.target.tagName.toUpperCase();
                if (tag != 'A' && tag != 'LI' && tag != 'SPAN' && tag != 'SUP') {
                    return;
                }

                var article = Article.get_by_node($(node));
                var type = $(ev.target).closest('li').attr('rel');

                return article._click_section(type);
            },

            _load_from_history: function(url, parent_page, parent, next_steps) {
                parent = (parent == Page && MainSearch.obj.is_active) ? MainSearch.obj : parent;
                // TODO : manage parent_page
                var $article_node = parent.get_article_container().find('article.content').find('> header > h1 > a[href="' + url + '"]').eq(0);
                if (!$article_node.length) {
                    return Page._load_items_from_history(next_steps,parent);
                }

                Page._set_last_history_url(Page.compute_url(url));

                var article = Article.get_by_node($article_node);
                return article._load_from_history(next_steps);
            },

            _on_toggle: function(flag, node, ev) {
                var article = Article.get_by_node($(node));
                return article._on_toggle(flag);
            },

            _on_show_user_tags_click: function(link, ev) {
                $(link).parent().children('ul.user-tags').toggleClass('opened');
                return false;
            },

            _on_edit_note_click: function(link, ev) {
                var article = Article.get_by_node($(link));
                return article.edit_note();
            },

            _on_cancel_note: function(link, ev) {
                var article = Article.get_by_node($(link));
                return article.stop_edit_note();
            },

            _on_note_form_input_click: function(input, ev) {
                var article = Article.get_by_node($(input));
                return article.on_note_form_input_click(input);
            },

            _on_save_note: function(form, ev) {
                var article = Article.get_by_node($(form));
                return article.save_note();
            },

            _on_owner_click: function(link, ev) {
                var $article = $(link).parents('article.content').first();
                if ($article.length) {
                    Article.get_by_node($article).load_section('owner');
                }
                return false;
            },

            _on_parent_fork_click: function(link, ev) {
                var $article = $(link).parents('article.content').first();
                if ($article.length) {
                    Article.get_by_node($article).load_section('parent_fork');
                }
                return false;
            },

        _void: null}, // __classvars__

        __init__: function(url) {
            this.$super();

            this.url = url;
            if (url.indexOf('/user/') == 0) {
                this.type = 'account';
                this.search_type = 'people';
            } else {
                this.type = 'repository';
                this.search_type = 'repositories';
            }
            Article._add_by_url(this);

            this._sections = {};
            this.current_section = null;
            this.$details = null;

            this._parent_page = 1;

        },

        _click: function() {
            if (this.$node.hasClass('with-opened')) {
                this.close_opened_children();
                return false;
            }
            return this.is_opened() ? this.close(true) : this.open();
        },

        get_parent: function() {
            var $parent = this.$node.closest('section.details > section.current');
            if ($parent.length) {
                return Section.get_by_node($parent);
            }
            if (MainSearch.obj.is_active) {
                return MainSearch.obj;
            }
            return Page;
        },

        get_state_data: function() {
            return ['Article', this.url, this.get_page()];
        },

        get_page: function() {
            var page = this.$node.attr('data-page');
            if (!page) { page = 1; }
            return page;
        },

        is_opened: function() {
            return (this.$node && this.$node.length && this.$node.hasClass('with-details') && this.has_details());
        },

        open: function(callback) {
            if (this.is_loading || this.is_opened()) { return false; }
            return this.load(callback);
        },

        load: function(callback) {
            if (!callback) { callback = this._on_details_loaded; }
            this._remove_details();
            this.$node.addClass('with-details');
            this.set_parent_with_opened(true);
            this._set_loading(true);
            this._ajax(callback);
            return false;
        },

        _load_from_history: function(next_steps) {
            this.load(function(details, ajax_params) {
                this._on_details_loaded(details, ajax_params);
                if (!next_steps.length) {
                    Page.set_title(this.get_title());
                }
                Page._load_items_from_history(next_steps, this);
            });
            return false;
        },

        close_opened_children: function() {
            if (!this.has_details()) { return; }
            this.current_section.$node.find('> section.results > article.content.with-details').each(function() {
                var article = Article.get_by_node($(this));
                article.close(false);
            });
            if (this.current_section) {
                this.current_section._add_to_history();
            } else {
                // shouldn't happen
                this._add_to_history();
            }
        },

        close: function(add_parent_to_history) {
            if (!this.is_opened()) { return false; }
            if (add_parent_to_history) {
                this.get_parent()._add_to_history();
            }
            this.set_parent_with_opened(false);
            this.$node.removeClass('with-details');
            this._remove_details();
            Node.scroll_to(this.$node, true);
            return false;
        },

        set_parent_with_opened: function(toggle) {
            var parent = this.get_with_openable_parent();
            if (parent) {
                parent.set_with_opened(toggle, true);
            }
        },

        _on_details_loaded: function(details, ajax_params) {
            this._set_loading(false);
            if (!this.$node) { return; }
            this.$node.append(details);
            this._set_details();
            this._add_to_history();
            this._add_close_button();
            this._find_existing_sections(true);
            Node.scroll_to(this.$node, true);
        },

        _add_close_button: function() {
            var $closer = this.$node.children('.close');
            if (!$closer.length) {
                $closer = $('<div/>').addClass('close').text('X').attr('title', 'Close this detail');
                this.$node.append($closer);
            }
        },

        _set_node: function($node) {
            this.$super($node);
            this._set_details();
        },

        _set_details: function() {
            var $details = this.$node.children('section.details');
            if ($details && $details.length) {
                this.$details = $details;
            } else {
                this.$details = null;
            }
        },

        has_details: function() {
            this._set_details();
            return (this.$details && this.$details.length);
        },

        _remove_details: function() {
            this.$node.children('section.details').remove();
            this.$details = null;
            this.set_current_section(null);
            this.set_with_opened(false, true);
        },

        _compute_title: function() {
            var header = this.$node.children('header'),
                name = header.children('h1').children('a').text().trim(),
                owner = header.children('h2').children('a:last-child').text().trim(),
                backend = header.children('h3').text().trim().replace(' ', '');
            this._title = '`' + (owner ? owner + '/' : '') + name + '` ' + backend;
        },

        get_section: function(type) {
            if (type in this._sections) {
                return this._sections[type];
            } else {
                return Section(this, type);
            }
        },

        load_section: function(type) {
            if (this.has_details()) {
                this._click_section(type);
                return;
            }
            this.load(function(details, ajax_params) {
                this._on_details_loaded(details, ajax_params);
                this.load_section(type);
            });
        },

        _click_section: function(type) {
            var section = this.get_section(type);
            if (section == this.current_section && section.is_opened()) {
                // it's already the opened section
                return false;
            }
            this._remove_sections();
            return section.open();
        },

        _remove_sections: function() {
            this.$node.children('section.details').children('section').remove();
            this.set_current_section(null);
        },

        set_current_section: function(section) {
            var $details = this.$node.children('section.details');
            if (!$details) { return; }
            if (section) {
                $details.children('section[rel!=' + section.type + ']').removeClass('current');
                if (section.$node) {
                    section.$node.addClass('current');
                }
                this.current_section = section;
                $details.find('> header li[rel!=' + section.type + ']').removeClass('current');
                $details.find('> header li[rel=' + section.type + ']').addClass('current');
            } else {
                $details.children('section').removeClass('current');
                $details.find('> header li').removeClass('current');
            }
        },

        _prepare_existing: function() {
            this.$node.addClass('with-details');
            this._set_details();
            AjaxCache.set(AjaxCache.key(this.url), this.$details);
            this._find_existing_sections(true);
            if (!Page._last_history_url && this.url == Page.url) {
                this._add_to_history(null, true);
            }
            if (!this.current_section) {
                Page.set_title(this.get_title());
            }
            if (Page.subsection == 'edit_tags') {
                TagManager.obj.open(this);
            } else if (Page.subsection == 'edit_note') {
                this.edit_note();
            }
            this.set_parent_with_opened(true);
        },

        _find_existing_sections: function(active_current) {
            var current = null;
            this.$details.find('> section').each(function(index) {
                var $section = $(this),
                    section = Section.get_by_node($section);
                section._prepare_existing();
                if (active_current && !current && $section.hasClass('current')) {
                    section.set_current();
                    current = section;
                } else {
                    section.$node.remove();
                }
            });
            this.set_current_section(current);
        },

        _on_toggle: function(flag) {
            var selector = '> footer > section > ul.actions > li.action-' + flag,
                $form = this.$node.find(selector).children('form');
            if (!$form.length) { return; }
            var that =this;
            $form.closest('li').addClass('loading');
            var reset = function() {
                $(this).find(selector).removeClass('loading');
            }
            $.post($form.attr('action'), $form.serialize())
                .success(function(data) {
                    if (data.error) {
                        Page.error(data.error, data.login_required);
                        that.run_for_all_nodes(reset);
                    } else {
                        that.run_for_all_nodes(function() {
                            $(this).find(selector)
                                .toggleClass('selected', data.is_set)
                                .removeClass('loading')
                                .children('form')
                                    .children('button').attr('title', data.title);
                        });
                    }
                    AjaxCache.clear(true);
                })
                .error(function() {
                    Page.error(xhr.responseText);
                    that.run_for_all_nodes(reset);
                });
            return false;
        },

        get_all_nodes: function() {
            return $('article.content:has(>header>h1>a[href="' + this.url + '"])');
        },

        run_for_all_nodes: function(callback) {
            var article = this;
            this.get_all_nodes().each(callback);
        },

        edit_note: function() {
            var $li = this.$node.find('> footer > section > ul.actions > li.action-note'),
                url = $li.children('a').attr('href'),
                $form = $li.children('form');
            if ($form.length) {
                $form.find('textarea').focus();
                return false;
            }
            $li.addClass('loading');
            Page.$overlay.show();
            $.get(url)
                .success(function(data) {
                    if (data.error) {
                        Page.$overlay.hide();
                        Page.error(data.error, data.login_required);
                    } else {
                        $li.append(data).addClass('edit');
                        $li.children('form').find('textarea').focus();
                    }
                })
                .error(function(xhr) {
                    Page.error(xhr.responseText);
                    Page.$overlay.hide();
                })
                .complete(function() {
                    $li.removeClass('loading');
                });
            return false;
        },

        stop_edit_note: function() {
            var $li = this.$node.find('> footer > section > ul.actions > li.action-note');
            $li.removeClass('loading edit');
            $li.children('form').remove();
            Page.$overlay.hide();
            return false;
        },

        on_note_form_input_click: function(input) {
            var $li = this.$node.find('> footer > section > ul.actions > li.action-note'),
                $form = $li.children('form'),
                $hidden = $form.find('input[type=hidden][name=delete]'),
                $input = $(input);
            if ($input.attr('name') == 'delete') {
                if (!$hidden.length) {
                    $hidden = $('<input />').attr('type', 'hidden').attr('name', 'delete').attr('value', $input.val());
                    $form.append($hidden);
                }
            } else {
                $hidden.remove();
            }
        },

        save_note: function() {
            var $li = this.$node.find('> footer > section > ul.actions > li.action-note'),
                $form = $li.children('form'),
                that = this;
            $li.addClass('loading');
            $.post($form.attr('action'), $form.serialize())
                .success(function(data) {
                    if (data.error) {
                        Page.error(data.error, data.login_required);
                    } else {
                        var rendered_note = typeof(data.note_rendered) == 'undefined' ? '' : data.note_rendered;
                        that.run_for_all_nodes(function() {
                            Article.get_by_node($(this)).update_note(rendered_note);
                        });
                        Page.message(data.message);
                        that.stop_edit_note();
                    }
                })
                .error(function(xhr) {
                    Page.error(xhr.responseText);
                })
                .complete(function() {
                    $li.removeClass('loading');
                });
            return false;
        },

        update_note: function(rendered_note) {
            var $li = this.$node.find('> footer > section > ul.actions > li.action-note'),
                $blockquote = $li.children('blockquote');
            rendered_note = rendered_note.trim();
            if (rendered_note) {
                if (!$blockquote.length) {
                    $blockquote = $('<blockquote/>');
                    $blockquote.append('<div />');
                    $li.append($blockquote);
                }
                $blockquote.children('div').html(rendered_note);
                $li.addClass('selected');
            } else {
                $li.removeClass('selected');
                if ($blockquote.length) {
                    $blockquote.remove();
                }
            }
        },

    _void: null}); // Article


    var Section = PageableContent.$extend({

        __classvars__: {
            _manage_events: function() {
                Page.doc.delegate('section.details > section.current > section.search form', 'submit', function(ev) {
                    return Section._on_filter_submit(this, ev);
                });
                Page.doc.delegate('section.details > section.current > section.search form button', 'click', function(ev) {
                    return Section._on_filter_button_click(this, ev);
                });
                Page.doc.delegate('section.details > section > section.results', 'page_loaded', function(ev, page) {
                    return Section._on_page_loaded(this, ev, page);
                });
            },

            __init__: function() {
                Section._manage_events();
            },

            get_by_node: function($node) {
                var $section = $node.closest('section.details > section[rel]'),
                    article = Article.get_by_node($section),
                    type = $section.attr('rel'),
                    section = article.get_section(type);
                section._set_node($section);
                return section;
            },

            _on_filter_submit: function(node, ev) {
                var $form = $(node),
                    section = Section.get_by_node($form);
                return section._on_filter_submit($form);
            },

            _on_filter_button_click: function(node, ev) {
                var $button = $(node),
                    $form = $button.closest('form'),
                    name = $button.attr('name');
                if (name.indexOf('direct-') == 0) {
                    // we select the matching radio, to have consistent querystring, for caching
                    var real_name = name.substr(7),
                        value = $button.val();
                    $form.find('input[name=' + real_name + '][value=' + value + ']').prop('checked', true);
                }
                return Section._on_filter_submit($form.get(0), ev);
            },

            _on_page_loaded: function(node, ev, page) {
                var section = Section.get_by_node($(node));
                section._set_last_page(page);
                return false;
            },

            _load_from_history: function(type, querystring, parent, next_steps) {
                if (!(parent instanceof Article)) {
                    return Page._load_items_from_history(next_steps, parent);
                }
                var section = parent.get_section(type);
                Page._set_last_history_url(Page.compute_url(section.url, querystring));
                return section._load_from_history(querystring, next_steps);
            },

        _void: null}, // __classvars__

        __init__: function(article, type) {
            this.$super();
            this.article = article;
            this.type = type;

            this.article._sections[this.type] = this;

            this._compute_url();
            this.querystring = '';
        },

        _get_link: function() {
            if (!this.article.has_details()) { return null; }
            var link = this.article.$details.find('>header li[rel=' + this.type + '] a');
            if (link.length) { return link; }
            return null;
        },

        _compute_url: function() {
            var link = this._get_link();
            if (link) {
                this.url = link.attr('href');
            }
        },

        _get_link_title: function() {
            var link = this._get_link();
            if (!link) { return null; }
            var title = link.children('span').text();
            return title.trim();
        },

        get_parent: function() {
            return this.article;
        },

        get_article_container: function() {
            return this.$node.children('section.results');
        },

        get_state_data: function() {
            return ['Section', this.type, this.querystring];
        },

        is_opened: function() {
            this._set_node();
            return (this.$node && this.$node.length);
        },

        open: function(callback) {
            if (this.is_loading || this.is_opened()) { return false; }
            this.querystring = '';
            return this.load(callback);
        },

        load: function(callback, querystring) {
            if (!callback) { callback = this._on_content_loaded; }
            this.set_current();
            this._set_last_page(1);
            this._set_loading(true);
            this._ajax(callback, querystring);
            return false
        },

        _load_from_history: function(querystring, next_steps) {
            this.querystring = querystring
            this.load(function(details, ajax_params) {
                this._on_content_loaded(details, ajax_params);
                if (!next_steps.length) {
                    Page.set_title(this.get_title());
                }
                Page._load_items_from_history(next_steps, this);
            }, querystring);
            return false;
        },

        close: function() {
            if (!this.is_opened()) { return false; }
            this.$node.remove();
            this._set_node(null);
            return false;
        },

        _add_to_history: function(querystring, replace_current) {
            if (!querystring) { querystring = this.querystring; }
            return this.$super(querystring, replace_current);
        },

        _on_content_loaded: function(content, ajax_params) {
            this._set_loading(false);
            if (!this.article.is_opened()) { return; }
            this.article.$details.append(content);
            this._set_node();
            this.set_current();
            Node.scroll_to(this.article.$node, true);
            this._set_last_page(1);
            this._add_to_history(ajax_params.querystring);
            if (!ajax_params.from_cache && !ajax_params.querystring) {
                this._copy_cache_to_form_cache();
            }
            Page._manage_input_clear(this.$node);
            Article._prepare_existing(this.$node);
        },

        _copy_cache_to_form_cache: function() {
            var $search_form = this.get_filter_form();
            if (!$search_form || !$search_form.length) { return; }
            var cache_key = AjaxCache.key(this.url);
                form_cache_key = AjaxCache.key(this.url, $search_form.serialize());
            AjaxCache.copy(cache_key, form_cache_key);
        },

        get_filter_form: function() {
            if (!this.$node) { return null; }
            return this.$node.find('section.search form');
        },

        set_current: function() {
            this.article.set_current_section(this);
            Page.set_title(this.get_title());
        },

        _on_filter_submit: function($form) {
            var $input_q = $form.find('input[name=q]');
            $input_q.val($input_q.val().trim());
            this.querystring = $form.serialize();
            this.article._remove_sections();
            return this.load(null, this.querystring);
        },

        _set_node: function($node) {
            if (!$node || !$node.length) {
                $node = this.article.$details.children('section[rel=' + this.type + ']');
                if (!$node.length) { $node = null; }
            }
            this.$super($node);
        },

        _get_loading_parent_node: function() {
            return this.article.$details;
        },

        _compute_title: function() {
            var title = this._get_link_title() || this.type;
            this._title = title + ' for ' + this.article.get_title();
        },

        _prepare_existing: function() {
            var cache_key = AjaxCache.key(this.url);
            AjaxCache.set(cache_key, this.$node);
            this._copy_cache_to_form_cache();
            if (!Page._last_history_url && this.url == Page.url) {
                this._add_to_history(null, true);
            }
        },

        get_title: function() {
            var title = this.$super();
            var $form = this.get_filter_form();
            if (!$form || !$form.length) { return title; }
            // add the search query
            var q = $form.find('input[name=q]').val();
            if (q) {
                title = "Search for `" + q + "` in " + title;
            }
            var final_parts = [];
            // add search options
            $form.find('fieldset.search_options input:checked').each(function() {
                final_parts.push($(this).next().text().replace(' ?', ''));
            });
            // add search order
            var $input_sort = $form.find('fieldset.search_order input[name=order]:checked');
            if ($input_sort.val()) {
                final_parts.push('Sort by ' + $input_sort.next().text());
            }
            // finalize
            if (final_parts.length) {
                title += ' (' + final_parts.join(', ') + ')'
            }
            return title;
        },

        set_with_opened: null,

    _void: null}); // Section


    Page.init();

    $.extend(window.Reposio, {
            Node: Node,
            Page: Page,
            MainSearch: MainSearch.obj,
            Articles: Article._by_url,
            AjaxCache: AjaxCache,
            TagManager: TagManager.obj
        }
    );

});

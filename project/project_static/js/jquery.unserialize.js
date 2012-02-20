// Unserialize (to) form plugin
// Version 1.0.5
// Copyright (C) 2010-2011 Christopher Thielen, others (see ChangeLog below)
// Dual-licensed under GPLv2 and the MIT open source licenses

// Usage:
//        var s = $("form").serialize(); // save form settings
//        $("form").unserializeForm(s);  // restore form settings

// Notes:
//        * Recurses fieldsets, p tags, etc.
//        * Form elements must have a 'name' attribute.

// Alternate Usage:
//        var s = $("form").serialize();
//        $("form").unserializeForm(s, {
//          'callback'        : function(el, val) { $(el).val(val); },
//          'override-values' : false
//        });
//
//        callback (optional):
//          The above callback is given the element and value, allowing you to build
//          dynamic forms via callback. If you return false, unserializeForm will
//          try to find and set the DOM element, otherwise, (on true) it assumes you've
//          handled that attribute and moves onto the next.
//        override-values (optional, default is false):
//          Controls whether elements already set (e.g. an input tag with a non-zero length value)
//          will be touched by the unserializer. Does not apply to radio fields or checkboxes.
//          If you have a use case for radio fields or checkboxes, please file an issue at
//          https://github.com/cthielen/unserialize-to-form/issues/ . Also note this option
//          does not apply to a callback, i.e. a callback would still have the opportunity
//          to override a value even if this option is set to false. It is up to you as
//          the callback author to enforce the behavior you wish.

// See ChangeLog at end of file for history.

(function($) {
  var methods = {
    _unserializeFormSetValue : function( el, _value, override ) {
       if($(el).length > 1) {
     		// Assume multiple elements of the same name are radio buttons
     		$.each(el, function(i) {
     			if($(this).attr("value") == _value) {
     				// Check it
     				$(this).prop("checked", true);
     			} else {
     				// Uncheck it
     				$(this).prop("checked", false);
     			}
     		});
     	} else {
     		// Assume, if only a single element, it is not a radio button
     		if($(el).attr("type") == "checkbox") {
     			$(el).prop("checked", true);
     		} else {
     		  if(override) {
     		    $(el).val(_value);
     		  } else {
     		    if (!$(el).val()) {
              $(el).val(_value);
            }
     		  }
     		}
     	}
    }
  };

	// takes a GET-serialized string, e.g. first=5&second=3&a=b and sets input tags (e.g. input name="first") to their values (e.g. 5)
	$.fn.unserializeForm = function( _values, _options ) {

	  // Set up defaults
    var settings = $.extend( {
      'callback'         : undefined,
      'override-values'  : false
    }, _options);

	  return this.each(function() {
  		// this small bit of unserializing borrowed from James Campbell's "JQuery Unserialize v1.0"
  		_values = _values.split("&");
  		_callback = settings["callback"];
  		_override_values = settings["override-values"];

  		if(_callback && typeof(_callback) !== "function") {
  			_callback = undefined; // whatever they gave us wasn't a function, act as though it wasn't given
  		}

  		var serialized_values = new Array();
  		$.each(_values, function() {
  			var properties = this.split("=");

  			if((typeof properties[0] != 'undefined') && (typeof properties[1] != 'undefined')) {
  				serialized_values[properties[0].replace(/\+/g, " ")] = decodeURI(properties[1].replace(/\+/g, " "));
  			}
  		});

  		// _values is now a proper array with values[hash_index] = associated_value
  		_values = serialized_values;

  		// Start with all checkboxes and radios unchecked, since an unchecked box will not show up in the serialized form
  		$(this).find(":checked").prop("checked", false);

  		// Iterate through each saved element and set the corresponding element
  		for(var key in _values) {
  			var el = $(this).add("input,select,textarea").find("[name=\"" + unescape(key) + "\"]");
  			var _value = unescape(_values[key]);

  			if(_callback == undefined) {
  				// No callback specified - assume DOM elements exist
  				methods._unserializeFormSetValue(el, _value, _override_values);
  			} else {
  				// Callback specified - don't assume DOM elements already exist
  				var result = _callback.call(this, unescape(key), _value);

  				// If they return true, it means they handled it. If not, we will handle it.
  				// Returning false then allows for DOM building without setting values.
  				if(result == false) {
            var el = $(this).add("input,select,textarea").find("[name=\"" + unescape(key) + "\"]");
  					// Try and find the element again as it may have just been created by the callback
  					methods._unserializeFormSetValue(el, _value, _override_values);
  				}
  	    	}
  		}
		})
	}
})(jQuery);

// ChangeLog
// 2010-11-19: Version 1.0 release. Works on text, checkbox and select inputs.
// 2011-01-26: Version 1.0.1 release. Fixed regular expression search, thanks Anton.
// 2011-02-02: Version 1.0.2 release. Support for textareas & check for undefined values, thanks Brandon.
// 2011-10-19: Version 1.0.3 release:
//                                    * Fixed unescaping issue for certain encoding elements (@)
//                                    * Traverse saved elements instead of the form when unserializing
//                                    * Provide optional callback for building dynamic forms
//                                    * Fixed issue setting radio buttons
// 2011-11-11: Version 1.0.4 release:
//                                    * Use .attr() instead of .prop() for jQuery 1.6 compatibility (Edward Anderson)
//                                    * Restore unchecked checkboxes and radios (Edward Anderson)
// 2011-12-06: Version 1.0.5 release:
//                                    * Fixed an issue with certain UTF characters (Chinese cited, thanks hoka!)
//                                    * Implemented 'return this' chaining method as recommended in jQuery docs
//                                    * Encapsulated internal method to keep namespaces clean
//                                    * Changed second parameter to an options array to account for new option
//                                    * Added new option 'override-values', default to true, to control whether fields
//                                      with content should be touched by the unserializer


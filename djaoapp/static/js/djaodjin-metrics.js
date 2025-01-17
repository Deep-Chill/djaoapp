/* Copyright (c) 2022, Djaodjin Inc.
   see LICENSE
*/

(function (root, factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(['exports', 'jQuery'], factory);
    } else if (typeof exports === 'object' && typeof exports.nodeName !== 'string') {
        // CommonJS
        factory(exports, require('jQuery'));
    } else {
        // Browser true globals added to `window`.
        factory(root, root.jQuery);
        // If we want to put the exports in a namespace, use the following line
        // instead.
        // factory((root.djResources = {}), root.jQuery);
    }
}(typeof self !== 'undefined' ? self : this, function (exports, jQuery) {


// Calculate width of word
function marginLeftCalculation(text, defaultFont) {
  "use strict";
  var font = defaultFont || "normal 12px Arial";
  $("body").append("<div id=\"calculation_width\" style=\"font:" + font + ";\"><span>" + text + "</span></div>");
  var widthText = $("#calculation_width span").width();
  $("#calculation_width").remove();
  return widthText;
}

function drawChartBackground(chart){
  "use strict";

  $(".background-future").remove();
  var dateNow = (new Date()).getTime();
  var dateNowXpos = chart.xAxis.scale()(dateNow);
  var backHeight = chart.yAxis.scale()(chart.yAxis.scale().domain()[0]);
  var backWidth = chart.xAxis.scale()(chart.xAxis.scale().domain()[1]);

  if (dateNowXpos > backWidth){
    dateNowXpos = backWidth;
  }else if (dateNowXpos < 0){
    dateNowXpos = 0;
  }

  d3.select(".nv-groups").append("rect")
    .attr("class", "background-future")
    .attr("x", dateNowXpos)
    .attr("width", backWidth - dateNowXpos)
    .attr("height", backHeight)
    .attr("fill", "rgba(66,139,202, 0.2)");

  d3.select(".nv-groups").append("rect")
    .attr("class", "background-future")
    .attr("x", 0)
    .attr("width", dateNowXpos)
    .attr("height", backHeight)
    .attr("fill", "rgba(153,211,240, 0.2)");
}

// This function should be called with all parameters
// updateChart('#example', data, null, 1, [])
// Container should be a div, a svg element is automaticaly added
// dates must be moment objects in order to compute ticks accurately.
function updateChart(container, data, unit, dataScale, extra) {
    "use strict";
    dataScale = dataScale || 1;
    var defaults = {
        "decimal": ".",
        "thousands": ",",
        "grouping": [3],
        "currency": ["$", ""],
        "dateTime": "%a %b %e %X %Y",
        "date": "%m/%d/%Y",
        "time": "%H:%M:%S",
        "periods": ["AM", "PM"],
        "days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "shortDays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "shortMonths": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    };
    if( unit === "usd" || unit === "cad" ) {
        defaults["currency"] = ["$", ""];
    } else if( unit === "eur" ) {
        defaults["currency"] = ["", "\u20ac"];
    } else {
        defaults["currency"] = [unit, ""];
    }
    // XXX These should be derived from *-xs definitions in .scss files
    var chartMobileWidth = 600;
    var mobileBreakpoint = 576;
    var curr = d3.locale(defaults);
    nv.addGraph(function() {
        // clear any previous chart elements before adding new ones
        // remove svg and append it again to remove all previous attached events
        d3.select(container).selectAll("*").remove();
        d3.select(container).append("svg").attr("class", "chart-area");
        var maxY = 0;
        var dateTicks = [];
        var labels = data.length > 0 ? data[0].values : [];
        var j = 0;
        var i = 0;
        for( j = 0; j < data.length; ++j ) {
            var values = data[j].values;
            for( i = 0; i < values.length; ++i ) {
                if( values[i][1] > maxY ) { maxY = values[i][1]; }
            }
        }
        for( i = 0; i < labels.length; ++i ) {
            dateTicks.push(labels[i][0]);
        }

        var marginLeft = maxY * dataScale;
        if( unit ) {
            if (marginLeft > 1000000){
              marginLeft = curr.numberFormat("$,.0f")(marginLeft / 1000000) + "M";
            }else if (marginLeft > 1000){
              marginLeft = curr.numberFormat("$,.0f")(marginLeft / 1000) + "K";
            }else{
              marginLeft = curr.numberFormat("$,.2f")(marginLeft);
            }
        }

        // Dynamic margin left to Optimize display
        marginLeft = marginLeftCalculation(marginLeft) + 25;
        /* force the yAxis to start at zero in all cases. */
        maxY = (maxY + 1) * dataScale;

        var chart = nv.models.lineChart()
            .x(function(d) { return d[0]; })
            .y(function(d) { return d[1] * dataScale; })
            .margin({top: 50, right: 20, bottom: 60, left: marginLeft})
            .useInteractiveGuideline(true);

        if($(window).width() <= mobileBreakpoint){
            chart.width(chartMobileWidth);
        }

        chart.legend.key(function(d){return d.title ? d.title : d.slug; })
        chart.interactiveLayer.tooltip.contentGenerator(function(d) {
            var hoverDate = d.value;

            // Get original tooltip html
            var html = nv.models.lineChart().interactiveLayer.tooltip.contentGenerator()(d);

            // Change data into it.
            var $html = $(html);

            // If unit format the exact number
            if (unit){
              $.each($html.find("td.value"), function(index, element){
                var value = $(element).text();
                $(element).text(curr.numberFormat("$,.2f")(value));
              });
            }

            // Replacing slug with title
            $.each($html.find("td.key"), function(index, element){
                var title = data[index].title ?
                    data[index].title : data[index].slug;
                $(element).text(title);
            });

            // if extra data add it to tooltip
            if (extra && extra.length > 0){
              $.each(extra, function(index, element){
                var extraKey = element.slug;
                var extraValue = $.grep(element.values, function(v){
                  return hoverDate === v[0];
                })[0];
                if (extraValue){
                  var style = null;
                  if (index === 0){
                    style = "border-top:1px double black;";
                  }
                  var newRow = "<tr><td style=\"" + style + "\"></td><td class=\"key\"  style=\"" + style + "\">" + extraKey + "</td><td class=\"value\" style=\"" + style + "\">" + extraValue[1] + "</td></tr>";
                  $html.find("tbody").append(newRow);
                }
              });
            }
            // return html tooltip;
            return $html.prop("outerHTML");
        });

        // Pb on voronoi calculation when all value are zero
        // https://github.com/novus/nvd3/issues/873
        // disable voronoi until fix on nv.d3 2.0.0
        // https://github.com/novus/nvd3/pull/584
        chart.useVoronoi(false);

        chart.xAxis
            .axisLabel("Date")
            .showMaxMin(false)     // removes max and min as ticks in x-axis
            .tickValues(dateTicks) // forces ticks to match dates in tooltip
            .tickFormat(function(d) {
                if(d.date() !== 1 || d.hour() !== 0
                   || d.minute() !== 0 || d.second() !== 0 ) {
                    return d.format("MMM'YY*");
                }
                return d.clone().subtract(1, 'months').format("MMM'YY");
            });
        chart.xScale(d3.time.scale());

        chart.yAxis
            .showMaxMin(false);  //remove max and min in x axe
        if( unit ) {
            // If we have a unit display it along the axis.
            chart.yAxis
                .tickFormat(function(d) {
                    if (d > 1000000){
                      return curr.numberFormat("$,.0f")(d / 1000000) + "M";
                    }else if (d > 1000){
                      return curr.numberFormat("$,.0f")(d / 1000) + "K";
                    }else{
                      return curr.numberFormat("$,.2f")(d);
                    }
                });
        } else {
            chart.yAxis
                .tickFormat(function(d) {
                    if(dataScale === 1){
                        return d3.format("d")(d);
                    }
                    return d3.format(",.2f")(d);
                });
        }
        chart.forceY(0); // Force only 0 but allow resize if unchecked chart

        d3.select(container + " svg")
            .datum(data)
            .transition().duration(100)
            .call(chart);

        drawChartBackground(chart);
        function handleRerender(){
            // if we are on mobile, hardcode the width
            if($(window).width() <= mobileBreakpoint){
                chart.width(chartMobileWidth);
            } else {
                chart.width(false);
            }
            chart.update();
            // Add timeout to update background correctly.
            setTimeout(function(){
                drawChartBackground(chart);
            }, 500);
        }

        // XXX listening on the inner ``container`` does not trigger
        // the chart update so we listen to the event fired
        // in ``$(".dashboard-nav-toggle").click()``.
        $('.dashboard-container').resize(handleRerender);

        nv.utils.windowResize(handleRerender);

        return chart;
    });
}


function updateBarChart(container, data, unit, dataScale, extra) {
    "use strict";
    dataScale = dataScale || 1;
    var defaults = {
        "decimal": ".",
        "thousands": ",",
        "grouping": [3],
        "currency": ["$", ""],
        "dateTime": "%a %b %e %X %Y",
        "date": "%m/%d/%Y",
        "time": "%H:%M:%S",
        "periods": ["AM", "PM"],
        "days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "shortDays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "shortMonths": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    };
    if( unit === "usd" || unit === "cad" ) {
        defaults["currency"] = ["$", ""];
    } else if( unit === "eur" ) {
        defaults["currency"] = ["", "\u20ac"];
    } else {
        defaults["currency"] = [unit, ""];
    }
    var curr = d3.locale(defaults);
    nv.addGraph(function() {

        // clear any previous chart elements before adding new ones
        // remove svg and append it again to remove all previous attached events
        d3.select(container).selectAll("*").remove();
        d3.select(container).append("svg").attr("class", "chart-area");
        var chart = nv.models.multiBarChart()
            .reduceXTicks(true)   // If 'false', every single x-axis tick
                                  // label will be rendered.
            .rotateLabels(0)      // Angle to rotate x-axis labels.
            .showControls(false)  // Allow user to switch between 'Grouped'
                                  // and 'Stacked' mode.
            .groupSpacing(0.1);   // Distance between each group of bars.
        chart.xAxis
            .tickFormat(function(d) {
                if(d.date() !== 1 || d.hour() !== 0
                   || d.minute() !== 0 || d.second() !== 0 ) {
                    return d.format("MMM'YY*");
                }
                return d.clone().subtract(1, 'months').format("MMM'YY");
            });
        if( unit ) {
            // If we have a unit display it along the axis.
            chart.yAxis
                .tickFormat(function(d) {
                    if (d > 1000000){
                      return curr.numberFormat("$,.0f")(d / 1000000) + "M";
                    }else if (d > 1000){
                      return curr.numberFormat("$,.0f")(d / 1000) + "K";
                    }else{
                      return curr.numberFormat("$,.2f")(d);
                    }
                });
        } else {
            chart.yAxis
                .tickFormat(function(d) {
                    return d3.format(",.2f")(d);
                });
        }
        chart.forceY(0); // Force only 0 but allow resize if unchecked chart

        chart.x(function(d) { return d[0]; })
            .y(function(d) { return d[1] / 100; });

        d3.select(container + " svg")
            .datum(data)
            .transition().duration(100)
            .call(chart);

        nv.utils.windowResize(chart.update);
        return chart;
    });
}


    // attach properties to the exports object to define
    // the exported module properties.
    exports.updateChart = updateChart;
    exports.updateBarChart = updateBarChart;
}));

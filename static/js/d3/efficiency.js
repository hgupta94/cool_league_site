function drawEfficiencyChart(selector, data) {
  const el = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (!el) return;

  const margin = { top: 30, right: 80, bottom: 60, left: 60 };
  const totalW = 500;
  const totalH = 375;
  const W = totalW - margin.left - margin.right;
  const H = totalH - margin.top - margin.bottom;

  el.innerHTML = "";

  d3.select(el).style("position", "relative");
  const tooltip = d3.select(el).append("div")
    .style("position", "absolute")
    .style("background", "rgba(255,255,255,0.95)")
    .style("border", "1px solid rgba(0,0,0,0.1)")
    .style("border-radius", "6px")
    .style("padding", "6px 10px")
    .style("width", "160px")
    .style("box-sizing", "border-box")
    .style("font-size", "13px")
    .style("color", "rgba(0,0,0,0.7)")
    .style("pointer-events", "none")
    .style("box-shadow", "0 2px 6px rgba(0,0,0,0.1)")
    .style("display", "none");

  const svg = d3.select(el).append("svg")
    .attr("width", totalW)
    .attr("height", totalH)
    .attr("role", "img")
    .attr("aria-label", "Scatter plot of optimal points versus difference from optimal, by team");

  const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // Tight domains: hug the actual data range on both axes rather than
  // padding out to zero. A little breathing room (10%) is added on each
  // side so points near the edge aren't clipped or flush against the axis.
  const diffExtent = d3.extent(data, d => d.difference_from_optimal);
  const diffPad = (diffExtent[1] - diffExtent[0]) * 0.1 || 1;

  const xScale = d3.scaleLinear()
    .domain([diffExtent[0] - diffPad, diffExtent[1] + diffPad])
    .range([0, W]);

  const ptsExtent = d3.extent(data, d => d.optimal_lineup_score);
  const ptsPad = (ptsExtent[1] - ptsExtent[0]) * 0.1 || 1;

  const yScale = d3.scaleLinear()
    .domain([ptsExtent[0] - ptsPad, ptsExtent[1] + ptsPad])
    .range([H, 0]);

  const xMedian = d3.median(data, d => d.difference_from_optimal);
  const yMedian = d3.median(data, d => d.optimal_lineup_score);
  const effMedian = d3.median(data, d => d.efficiency);

  const textCol = "rgba(0,0,0,0.4)";
  const gridCol = "rgba(0,0,0,0.2)";

  // Grid lines
  g.selectAll(".grid-h").data(yScale.ticks(6)).join("line")
    .attr("x1", 0).attr("x2", W)
    .attr("y1", d => yScale(d)).attr("y2", d => yScale(d))
    .attr("stroke", gridCol)
    .attr("stroke-opacity", 0.5)
    .attr("stroke-width", 0.5);

  g.selectAll(".grid-v").data(xScale.ticks(6)).join("line")
    .attr("y1", 0).attr("y2", H)
    .attr("x1", d => xScale(d)).attr("x2", d => xScale(d))
    .attr("stroke", gridCol)
    .attr("stroke-opacity", 0.5)
    .attr("stroke-width", 0.5);

  // Axes
  g.append("g").call(
    d3.axisLeft(yScale).ticks(6)
  ).call(ax => {
    ax.select(".domain").remove();
    ax.selectAll(".tick line").remove();
    ax.selectAll("text").attr("fill", textCol).style("font-size", 12);
  });

  g.append("g").attr("transform", `translate(0,${H})`).call(
    d3.axisBottom(xScale).ticks(6)
  ).call(ax => {
    ax.select(".domain").attr("stroke", gridCol);
    ax.selectAll(".tick line").remove();
    ax.selectAll("text").attr("fill", textCol).style("font-size", 12);
  });

  // Axis labels
  svg.append('text')
    .attr('x', margin.left + W / 2)
    .attr('y', margin.top + H + margin.bottom - 15)
    .attr('text-anchor', 'middle')
    .attr('font-size', 14)
    .attr('fill', textCol)
    .text('Difference from Optimal');

  svg.append('text')
    .attr('transform', `translate(${margin.left - 42}, ${margin.top + H / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle')
    .attr('font-size', 14)
    .attr('fill', textCol)
    .text('Optimal Points');

  // Median reference lines
  g.append("line")
    .attr("x1", xScale(xMedian))
    .attr("x2", xScale(xMedian))
    .attr("y1", 0)
    .attr("y2", H)
    .attr("stroke", "#999")
    .attr("stroke-width", 1)
    .attr("stroke-opacity", 0.65)
    .attr("stroke-dasharray", "4,3");

  g.append("line")
    .attr("x1", 0)
    .attr("x2", W)
    .attr("y1", yScale(yMedian))
    .attr("y2", yScale(yMedian))
    .attr("stroke", "#999")
    .attr("stroke-width", 1)
    .attr("stroke-opacity", 0.65)
    .attr("stroke-dasharray", "4,3");

  // Median line labels
  g.append("text")
    .attr("x", xScale(xMedian))
    .attr("y", -6)
    .attr("text-anchor", "middle")
    .attr("font-size", 11)
    .attr("fill", "#999")
    .text(`Median: ${xMedian.toFixed(1)} / ${(effMedian * 100).toFixed(1)}%`);

  g.append("text")
    .attr("x", W + 4)
    .attr("y", yScale(yMedian) - 4)
    .attr("text-anchor", "start")
    .attr("font-size", 11)
    .attr("fill", "#999")
    .text(`Median: ${yMedian.toFixed(2)}`);

  function showTooltip(d) {
    const effLabel = (typeof d.efficiency === "number") ? (d.efficiency * 100).toFixed(1) + "%" : "N/A";
    tooltip
      .style("display", "block")
      .html(`<strong>${d.team}</strong><br>Optimal PPG: ${d.optimal_lineup_score.toFixed(2)}<br>Efficiency: ${effLabel}`);
  }

  function moveTooltip(event) {
    const [mx, my] = d3.pointer(event, el);
    const tooltipW = 160;
    const tooltipH = 70;
    const gap = 10;

    const fitsRight = mx + gap + tooltipW <= totalW - 5;
    const left = fitsRight ? mx + gap : mx - gap - tooltipW;

    const top = Math.max(Math.min(my - 28, totalH - tooltipH - 5), 5);
    tooltip.style("left", left + "px").style("top", top + "px");
  }

  function hideTooltip() {
    tooltip.style("display", "none");
  }

  // Points
  g.selectAll(".point")
    .data(data)
    .join("circle")
    .attr("class", "point")
    .attr("cx", d => xScale(d.difference_from_optimal))
    .attr("cy", d => yScale(d.optimal_lineup_score))
    .attr("r", 6)
    .attr("fill", d => TEAM_COLORS[d.team] ?? defaultColor)
    .attr("stroke", "#f5f5f5")
    .attr("stroke-width", 1.5)
    .style("cursor", "pointer")
    .on("mouseenter", function(event, d) {
      d3.select(this).attr("r", 8);
      showTooltip(d);
    })
    .on("mousemove", moveTooltip)
    .on("mouseleave", function(event, d) {
      d3.select(this).attr("r", 6);
      hideTooltip();
    });

  // Team labels next to each point
  g.selectAll(".point-label")
    .data(data)
    .join("text")
    .attr("class", "point-label")
    .attr("x", d => xScale(d.difference_from_optimal) + 10)
    .attr("y", d => yScale(d.optimal_lineup_score) + 4)
    .attr("font-size", 13)
    .attr("fill", textCol)
    .style("cursor", "pointer")
    .text(d => d.team)
    .on("mouseenter", function(event, d) { showTooltip(d); })
    .on("mousemove", moveTooltip)
    .on("mouseleave", hideTooltip);
}
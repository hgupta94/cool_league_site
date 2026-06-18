function drawTeamProbChart(selector, data, metric = "playoffs") {
  const el = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (!el) return;

  const teams = [...new Set(data.map(d => d.team))].sort();
  const margin = { top: 60, right: 80, bottom: 60, left: 45 };
  const totalW = 700;
  const totalH = 400;
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
    .style("font-size", "13px")
    .style("color", "rgba(0,0,0,0.7)")
    .style("pointer-events", "none")
    .style("box-shadow", "0 2px 6px rgba(0,0,0,0.1)")
    .style("display", "none");

  const legendH = 0;
  const svg = d3.select(el).append("svg")
    .attr("width", totalW)
    .attr("height", totalH + legendH)
    .attr("role", "img")
    .attr("aria-label", "Line chart of team probabilities by week");

  const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  const weeks = [...new Set(data.map(d => d.week))].sort((a, b) => a - b);
  const xScale = d3.scalePoint().domain(weeks).range([0, W]).padding(0);

  // y axis formatter
  const FRACTION_METRICS = new Set(["playoffs", "finals", "champion", "most_wins", "most_points", "third"]);
  const isFraction = FRACTION_METRICS.has(metric);
  const METRIC_LABELS = {
    playoffs: "Make Playoffs",
    third: "Third Place",
    finals: "Make Finals",
    champion: "Win Championship",
    most_wins: "Most Wins",
    most_points: "Most Points",
    matchup_wins: "Matchup Wins",
    tophalf_wins: "Top Half Wins",
    total_wins: "Total Wins",
    total_points: "Total Points",
    top_scores: "Top Score Weeks",
    xpo: "Expected Payout"
  };

  const values = data.map(d => d[metric]).filter(v => v != null);
  const yMax = d3.max(values) ?? 1;
  const yMin = d3.min(values) ?? 0;
  const yPadding = (yMax - yMin) * 0.05 || 0.05;

  const yScale = d3.scaleLinear()
    .domain(
      isFraction
        ? [0, 1]
        : metric === "total_points"
          ? [Math.floor((yMin - 100) / 100) * 100, Math.ceil((yMax + 100) / 100) * 100]
          : [Math.min(0, yMin), yMax + yPadding]
    )
    .range([H, 0]);

  const textCol = "rgba(0,0,0,0.4)";
  const gridCol = "rgba(0,0,0,0.2)";

  // Grid lines
  g.selectAll(".grid-h").data(yScale.ticks(5)).join("line")
    .attr("x1", 0).attr("x2", W)
    .attr("y1", d => yScale(d)).attr("y2", d => yScale(d))
    .attr("stroke", gridCol).attr("stroke-width", 0.5);

  // Axes
  g.append("g").call(
    d3.axisLeft(yScale).ticks(5).tickFormat(d =>
      isFraction ? Math.round(d * 100) + "%" :
      metric === "xpo" ? "$" + d3.format(",.0f")(d) :
      d3.format(",.0f")(d)
    )
  ).call(ax => {
    ax.select(".domain").remove();
    ax.selectAll(".tick line").remove();
    ax.selectAll("text").attr("fill", textCol).style("font-size", 12);
  });

  g.append("g").attr("transform", `translate(0,${H})`).call(
    d3.axisBottom(xScale).tickFormat(d => d)
  ).call(ax => {
    ax.select(".domain").attr("stroke", gridCol);
    ax.selectAll(".tick line").remove();
    ax.selectAll("text").attr("fill", textCol).style("font-size", 12);
  });

  const teamData = d3.group(data, d => d.team);

  // Invisible wide hit-area paths for easier hover targeting
  teamData.forEach((rows, team) => {
    const sorted = rows.sort((a, b) => a.week - b.week);
    const lineGen = d3.line()
      .x(d => xScale(d.week))
      .y(d => yScale(d[metric]))
      .curve(d3.curveMonotoneX)
      .defined(d => d[metric] != null);

    g.append("path")
      .datum(sorted)
      .attr("fill", "none")
      .attr("stroke", "transparent")
      .attr("stroke-width", 20)
      .attr("d", lineGen)
      .on("mouseenter", () => setHighlight(team))
      .on("mouseleave", () => setHighlight(null));
  });

  // Lines + dots
  teamData.forEach((rows, team) => {
    const color = TEAM_COLORS[team];
    const sorted = rows.sort((a, b) => a.week - b.week);

    const lineGen = d3.line()
      .x(d => xScale(d.week))
      .y(d => yScale(d[metric]))
      .curve(d3.curveMonotoneX)
      .defined(d => d[metric] != null);

    g.append("path")
      .datum(sorted)
      .attr("data-team", team)
      .attr("fill", "none")
      .attr("stroke", color)
      .attr("stroke-width", 2)
      .attr("opacity", 0.85)
      .attr("d", lineGen)
      .on("mouseenter", () => setHighlight(team))
      .on("mouseleave", () => setHighlight(null));

    // hover tooltip over points
    sorted.forEach(d => {
      g.append("circle")
        .attr("data-team", team)
        .attr("cx", xScale(d.week))
        .attr("cy", yScale(d[metric]))
        .attr("r", 3.5)
        .attr("fill", color)
        .attr("stroke", "#f5f5f5")
        .attr("stroke-opacity", 0.85)
        .attr("stroke-width", 1.5)
        .on("mouseenter", function(event) {
          setHighlight(team);
          const label = isFraction
            ? (d[metric] * 100).toFixed(1) + "%"
            : (metric === "xpo" ? "$" : "") + d3.format(",.2f")(d[metric]);
          tooltip
            .style("display", "block")
            .html(`<strong>${team}</strong><br>Week ${d.week}<br>${METRIC_LABELS[metric] ?? metric}: ${label}`);
        })
        .on("mousemove", function(event) {
          tooltip
            .style("left", (event.offsetX + 14) + "px")
            .style("top", (event.offsetY - 28) + "px");
        })
        .on("mouseleave", function() {
          setHighlight(null);
          tooltip.style("display", "none");
        });
    });
  });

  function setHighlight(hoveredTeam) {
  svg.selectAll("[data-team]").each(function() {
    const el = d3.select(this);
    const isMatch = this.dataset.team === hoveredTeam;
    const isPath = this.tagName === "path";
    const isCircle = this.tagName === "circle";
    const isG = this.tagName === "g";

    if (hoveredTeam === null) {
      // reset everything
      if (isPath)   el.attr("opacity", 0.85).attr("stroke-width", 2);
      if (isCircle) el.attr("opacity", 1).attr("r", 3.5).style("display", null);
      if (isG)      el.attr("opacity", 1).attr("font-size", 15);
    } else {
      if (isPath)   el.attr("opacity", isMatch ? 1 : 0.1).attr("stroke-width", isMatch ? 3 : 2);
      if (isCircle) el.attr("opacity", isMatch ? 1 : 0.1).attr("r", isMatch ? 5 : 3.5).style("display", isMatch ? null : "none");
      if (isG)      el.attr("opacity", isMatch ? 1 : 0.3).attr("font-size", 14);
    }
  });
}

  // Title
<!--  svg.append('text')-->
<!--  .attr('x', margin.left + W / 2)-->
<!--  .attr('y', 35)-->
<!--  .attr('text-anchor', 'middle')-->
<!--  .attr('font-size', 32)-->
<!--  .attr('font-weight', 500)-->
<!--  .attr('fill', 'rgba(0,0,0,0.7)')-->
<!--  .text(METRIC_LABELS[metric] ?? metric);-->

  // X label
  svg.append('text')
  .attr('x', margin.left + W / 2)
  .attr('y', margin.top + H + margin.bottom - 15)
  .attr('text-anchor', 'middle')
  .attr('font-size', 16)
  .attr('fill', 'rgba(0,0,0,0.5)')
  .text('Week');

  // Legend
  const numTeams = teams.length;
  const itemSpacing = 20;
  const totalLegendHeight = numTeams * itemSpacing;

  const legend = svg.append("g")
    .attr("transform", `translate(${margin.left + W + 15}, ${margin.top + (H - totalLegendHeight) / 2})`);

  teams.forEach((team, i) => {
    const gItem = legend.append("g")
      .attr("data-team", team)
      .attr("transform", `translate(0, ${i * itemSpacing})`)
      .style("cursor", "pointer")
      .style("pointer-events", "all")
      .on("mouseenter", () => setHighlight(team))
      .on("mouseleave", () => setHighlight(null));

    gItem.append("rect")
      .attr("width", 12).attr("height", 12).attr("rx", 2)
      .attr("fill", TEAM_COLORS[team]);

    gItem.append("text")
      .attr("x", 17).attr("y", 10)
      .attr("font-size", 14)
      .attr("fill", TEAM_COLORS[team])
      .text(team);
  });
}
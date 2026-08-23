/**
 * createOddsChart — renders an interactive multi-team odds/points line chart using D3.js
 *
 * @param {string|HTMLElement} container  CSS selector or DOM element to render into
 * @param {Array<{date: string, team: string, p_win: number, p_tophalf: number, p_highest: number, p_lowest: number, avg_score: number}>} data
 *        One row per team per date. The four odds fields are win probabilities
 *        expressed as 0-1 fractions (e.g. 0.4901) and are converted to American
 *        odds. `avg_score` is a raw projected-points value and is plotted on its
 *        own linear axis.
 * @param {Object} [options]
 * @param {number} [options.width=780]             Total SVG width in px
 * @param {number} [options.height=380]            Total SVG height in px
 * @param {Object} [options.margin]                {top, right, bottom, left}
 * @param {Array<{key: string, label: string, type?: 'odds'|'value', scale?: number}>} [options.metrics]
 *        Selectable metrics for the "Market" dropdown. `type: 'odds'` (the default)
 *        plots on the American-odds axis and expects a probability; `scale` is the
 *        multiplier applied to that raw value to get a 0-100 percentage (100 for a
 *        0-1 fraction like p_win, 1 if your data is already 0-100). `type: 'value'`
 *        plots on a plain linear axis spanning the metric's own min/max and ignores
 *        `scale`. Defaults to the four odds fields plus avg_score.
 * @param {string} [options.dateField='date']      Name of the date field on each row (format YYYY-MM-DD)
 * @param {string} [options.initialMetric]         Metric key shown on first render (defaults to metrics[0].key)
 * @param {Object} [options.teamColors]            Optional {teamName: cssColor} map. Falls back to a
 *                                                  global TEAM_COLORS object if one is in scope, then to
 *                                                  an auto-generated palette.
 * @param {number} [options.oddsMin=100]           Odds magnitude at the center of the axis (the ±100 seam)
 * @param {number} [options.oddsMax=10000]         Odds magnitude at the outer edge of the axis
 * @param {number} [options.valuePadding=0.12]     Fraction of the min/max range added as headroom
 *                                                  above and below a 'value' metric's axis
 * @returns {SVGSVGElement} the rendered <svg> node
 */
function createOddsChart(container, data, options = {}) {
  const {
    width = 780,
    height = 380,
    margin = { top: 10, right: 150, bottom: 50, left: 62 },
    metrics = [
      { key: 'p_win', label: 'Matchup Win', type: 'Odds', scale: 100 },
      { key: 'p_tophalf', label: 'Top Half Win', type: 'Odds', scale: 100 },
      { key: 'p_highest', label: 'Highest Score', type: 'Odds', scale: 100 },
      { key: 'p_lowest', label: 'Lowest Score', type: 'Odds', scale: 100 },
      { key: 'avg_score', label: 'Projected Points', type: 'value' }
    ],
    dateField = 'date',
    initialMetric = metrics[0].key,
    teamColors = null,
    oddsMin = 100,
    oddsMax = 10000,
    valuePadding = 0.12
  } = options;

  const ODDS_MIN = oddsMin;
  const ODDS_MAX = oddsMax;

  const el = typeof container === 'string' ? document.querySelector(container) : container;
  el.innerHTML = '';
  d3.select(el).style('position', 'relative');

  const parseDate = d3.timeParse('%Y-%m-%d');
  const dayFmt = d3.timeFormat('%a');
  const fullDayFmt = d3.timeFormat('%b %-d');

  const parsed = data.map(d => ({ ...d, date: parseDate(d[dateField]) }));
  const teams = Array.from(new Set(parsed.map(d => d.team)));
  const grouped = d3.group(parsed, d => d.team);

  const colorRamp = ['#7F77DD', '#1D9E75', '#D85A30', '#D4537E', '#378ADD', '#BA7517'];
  const fallbackColor = d3.scaleOrdinal().domain(teams).range(colorRamp);
  const teamColor = team =>
    (teamColors && teamColors[team]) ||
    (typeof TEAM_COLORS !== 'undefined' && TEAM_COLORS[team]) ||
    fallbackColor(team);

  const axisColor = 'rgba(0,0,0,0.35)';
  const textColor = 'rgba(0,0,0,0.5)';
  const gridColor = 'rgba(0,0,0,0.07)';
  const titleColor = 'rgba(0,0,0,0.75)';

  function metricConfig(key) {
    return metrics.find(m => m.key === key) || { key, label: key, type: 'odds', scale: 1 };
  }

  // raw field value -> 0-100 percentage, using that metric's configured scale
  function metricPct(d, metric) {
    const { scale = 1 } = metricConfig(metric);
    return d[metric] * scale;
  }

  // ---- convert win probability (0-100) to American odds ----
  function pctToOdds(pct) {
    if (pct <= 0) return -Infinity;
    if (pct >= 100) return Infinity;
    const p = pct / 100;
    return p >= 0.5 ? -100 * p / (1 - p) : 100 * (1 - p) / p;
  }

  // ---- map finite odds -> axis position in [0,1] ----
  function oddsToAxisPos(odds) {
    const mag = Math.min(Math.max(Math.abs(odds), ODDS_MIN), ODDS_MAX);
    const logFrac = (Math.log10(mag) - Math.log10(ODDS_MIN)) /
                    (Math.log10(ODDS_MAX) - Math.log10(ODDS_MIN));
    return odds < 0 ? 0.5 - 0.5 * logFrac : 0.5 + 0.5 * logFrac;
  }

  function oddsLabel(pct) {
    const odds = pctToOdds(pct);
    if (!isFinite(odds)) return odds > 0 ? 'Locked \u2713' : 'Eliminated \u2715';
    const r = Math.round(odds / 5) * 5;
    return (r > 0 ? '+' : '') + r;
  }

  // ---- controls ----
  const controls = d3.select(el).append('div')
    .style('display', 'flex')
    .style('justify-content', 'center')
    .style('gap', '18px')
    .style('margin-bottom', '12px');

  function buildSelect(labelText) {
    const wrap = controls.append('label')
      .style('display', 'flex')
      .style('flex-direction', 'column')
      .style('gap', '4px')
      .style('font-size', '11px')
      .style('text-transform', 'uppercase')
      .style('letter-spacing', '0.06em')
      .style('color', textColor);
    wrap.append('span').text(labelText);
    return wrap.append('select')
      .style('font-size', '16px')
      .style('padding', '6px 10px')
      .style('border-radius', '6px')
      .style('border', `1px solid ${gridColor}`)
      .style('background', '#f0f0f0')
      .style('color', '#111');
  }

  const metricSelect = buildSelect('');
  metricSelect.selectAll('option')
    .data(metrics).enter()
    .append('option').attr('value', d => d.key).text(d => d.label);
  metricSelect.property('value', initialMetric);

  // ---- tooltip ----
  const tooltip = d3.select(el).append('div')
    .style('position', 'absolute')
    .style('pointer-events', 'none')
    .style('opacity', 0)
    .style('transition', 'opacity 100ms ease')
    .style('background', "rgba(255,255,255,0.95)")
    .style("color", "rgba(0,0,0,0.7)")
    .style('padding', '8px 10px')
    .style('border-radius', '7px')
    .style('font-size', '12px')
    .style('line-height', '1.5')
    .style('white-space', 'nowrap')
    .style('box-shadow', '0 6px 16px rgba(0,0,0,0.25)')
    .style('z-index', 10);

  function tooltipHtml(team, d, metric) {
    const { type } = metricConfig(metric);
    const valueLine = type === 'value'
      ? `${d[metric].toFixed(2)} pts`
      : `${Math.round(metricPct(d, metric))}% \u2022 ${oddsLabel(metricPct(d, metric))}`;
    return `
      <strong style="color:${teamColor(team)}">${team}</strong><br>
      ${dayFmt(d.date)}, ${fullDayFmt(d.date)}<br>
      ${valueLine}
    `;
  }

  function showTooltip(html, event) {
    const [px, py] = d3.pointer(event, el);
    tooltip
      .style('opacity', 1)
      .html(html)
      .style('left', `${px + 14}px`)
      .style('top', `${py - 28}px`);
  }

  function hideTooltip() {
    tooltip.style('opacity', 0);
  }

  const svg = d3.select(el).append('svg')
    .attr('width', width)
    .attr('height', height)
    .style('display', 'block')
    .style('margin-left', 'auto')
    .style('margin-right', 'auto')
    .style('max-width', '100%')
    .style('height', 'auto')
    .style('overflow', 'visible');

  // ---- hover helpers (operate on whatever the current render drew) ----
  function highlightTeam(team) {
    svg.selectAll('.team-line').each(function () {
      const line = d3.select(this);
      const match = line.attr('data-team') === team;
      line.attr('stroke-width', match ? 3.5 : 2).attr('opacity', match ? 1 : 0.2);
    });
    svg.selectAll('.team-stub').each(function () {
      const stub = d3.select(this);
      const match = stub.attr('data-team') === team;
      stub.attr('stroke-width', match ? 3.5 : 2).attr('opacity', match ? 1 : 0.15);
    });
    svg.selectAll('.team-dot').each(function () {
      const dot = d3.select(this);
      const match = dot.attr('data-team') === team;
      dot.attr('opacity', match ? 1 : 0.2).attr('r', match ? 5 : 3.5);
    });
    svg.selectAll('.team-icon').each(function () {
      const icon = d3.select(this);
      const match = icon.attr('data-team') === team;
      icon.attr('opacity', match ? 1 : 0.2);
      icon.select('.icon-circle').attr('r', match ? 8 : 6).attr('stroke-width', match ? 2.5 : 1.5);
      icon.select('.icon-check').attr('font-size', match ? '10px' : '8px');
    });
    svg.selectAll('.legend-row').each(function () {
      const row = d3.select(this);
      const match = row.attr('data-team') === team;
      row.attr('opacity', match ? 1 : 0.35).attr('font-weight', match ? '800' : '400');
    });
  }

  function clearHighlight() {
    svg.selectAll('.team-line').attr('stroke-width', 2).attr('opacity', 1);
    svg.selectAll('.team-stub').attr('stroke-width', 2).attr('opacity', 0.6);
    svg.selectAll('.team-dot').attr('opacity', 1).attr('r', 3.5);
    svg.selectAll('.team-icon').attr('opacity', 1).each(function () {
      const icon = d3.select(this);
      icon.select('.icon-circle').attr('r', 6).attr('stroke-width', 1.5);
      icon.select('.icon-check').attr('font-size', '8px');
    });
    svg.selectAll('.legend-row').attr('opacity', 1).attr('font-weight', '400');
  }

  function render() {
    svg.selectAll('*').remove();

    const metric = metricSelect.property('value');
    const { label: metricLabel, type: metricType } = metricConfig(metric);
    const isValueMetric = metricType === 'value';
    const filtered = parsed;
    const teamsToPlot = teams;
    const teamMatchupId = new Map();
    parsed.forEach(d => {
      if (!teamMatchupId.has(d.team) && d.matchup_id != null) {
       teamMatchupId.set(d.team, d.matchup_id);
      }
    });

    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleTime()
      .domain(d3.extent(filtered, d => d.date))
      .range([0, innerWidth]);

    // ---- y scale: American-odds axis for odds metrics, plain min/max axis for value metrics ----
    let y;
    if (isValueMetric) {
      const [minV, maxV] = d3.extent(filtered, d => d[metric]);
      const pad = (maxV - minV) * valuePadding || Math.max(Math.abs(maxV) * 0.1, 1);
      y = d3.scaleLinear().domain([minV - pad, maxV + pad]).range([innerHeight, 0]);
    } else {
      // Reverse only Odds: low axis-pos values render near bottom, high near top
      y = d3.scaleLinear().domain([0, 1]).range([0, innerHeight]);
    }

    // x-axis
    const uniqueDates = Array.from(new Set(filtered.map(d => +d.date)))
      .map(t => new Date(t))
      .sort((a, b) => a - b);

    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(x).tickValues(uniqueDates).tickFormat(dayFmt))
      .call(ax => ax.select('.domain').attr('stroke', axisColor))
      .call(ax => ax.selectAll('line').attr('stroke', axisColor))
      .call(ax => ax.selectAll('text').attr('fill', textColor).attr('font-size', 11));

    // y-axis
    const yAxisG = g.append('g');
    if (isValueMetric) {
      yAxisG
        .call(d3.axisLeft(y).ticks(6))
        .call(ax => ax.select('.domain').attr('stroke', axisColor))
        .call(ax => ax.selectAll('.tick line')
          .attr('stroke', gridColor)
          .attr('x2', innerWidth))
        .call(ax => ax.selectAll('text').attr('fill', textColor).attr('font-size', 10.5));
    } else {
      yAxisG.append('line')
        .attr('x1', 0).attr('x2', 0).attr('y1', 0).attr('y2', innerHeight)
        .attr('stroke', axisColor);

      const magTicks = [100, 300, 1000, 3000, 10000];
      magTicks.forEach(mag => {
        [-1, 1].forEach(sign => {
          const odds = sign * mag;
          if (mag === 100 && sign === -1) return; // draw +/-100 once
          const cy = y(oddsToAxisPos(odds));
          yAxisG.append('g')
            .attr('transform', `translate(0,${cy})`)
            .call(tick => {
              tick.append('line').attr('x1', -5).attr('x2', 0).attr('stroke', axisColor);
              tick.append('line').attr('x1', 0).attr('x2', innerWidth).attr('stroke', gridColor);
              tick.append('text')
                .attr('x', -10).attr('dy', '0.32em').attr('text-anchor', 'end')
                .attr('fill', textColor).attr('font-size', 10.5)
                .text(mag === 100 ? '\u00B1100' : (odds > 0 ? '+' + odds : odds));
            });
        });
      });

      // seam line at +/-100 — only meaningful on the odds axis
      g.append('line')
        .attr('x1', 0).attr('x2', innerWidth)
        .attr('y1', y(0.5)).attr('y2', y(0.5))
        .attr('stroke', axisColor)
        .attr('stroke-dasharray', '4,3');
    }

    // y-axis label
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(margin.top + innerHeight / 2))
      .attr('y', 16)
      .attr('text-anchor', 'middle')
      .attr('font-size', 12)
      .attr('fill', textColor)
      .text(metricLabel);

    // ---- line generator: raw value for 'value' metrics, odds position for 'odds' metrics ----
    const line = isValueMetric
      ? d3.line()
          .curve(d3.curveMonotoneX)
          .defined(d => d[metric] != null && isFinite(d[metric]))
          .x(d => x(d.date))
          .y(d => y(d[metric]))
      : d3.line()
          .curve(d3.curveMonotoneX)
          .defined(d => isFinite(pctToOdds(metricPct(d, metric))))
          .x(d => x(d.date))
          .y(d => y(oddsToAxisPos(pctToOdds(metricPct(d, metric)))));

    const bisectDate = d3.bisector(d => d.date).left;
    const iconsToDraw = [];
    const latestPointByTeam = new Map();

    teamsToPlot.forEach(team => {
      const teamData = [...(grouped.get(team) || [])].sort((a, b) => a.date - b.date);
      const latestPlottable = [...teamData].reverse().find(d =>
        isValueMetric
          ? (d[metric] != null && isFinite(d[metric]))
          : isFinite(pctToOdds(metricPct(d, metric)))
      );
      if (latestPlottable) {
        latestPointByTeam.set(team, latestPlottable);
      }

      g.append('path')
        .datum(teamData)
        .attr('class', 'team-line')
        .attr('data-team', team)
        .attr('fill', 'none')
        .attr('stroke', teamColor(team))
        .attr('stroke-width', 2)
        .attr('d', line)
        .style('cursor', 'pointer')
        .on('mousemove', function (event) {
          const [mx] = d3.pointer(event, g.node());
          const x0 = x.invert(mx);
          const idx = bisectDate(teamData, x0, 1);
          const dPrev = teamData[idx - 1];
          const dNext = teamData[idx];
          const nearest = !dNext ? dPrev
            : !dPrev ? dNext
            : (x0 - dPrev.date > dNext.date - x0 ? dNext : dPrev);
          if (!nearest) return;
          highlightTeam(team);
          showTooltip(tooltipHtml(team, nearest, metric), event);
        })
        .on('mouseleave', function () {
          clearHighlight();
          hideTooltip();
        });

      // "locked / eliminated" stubs only make sense for odds metrics —
      // a points projection doesn't hit 0% or 100%
      if (!isValueMetric) {
        const lastFinite = [...teamData].reverse().find(d => isFinite(pctToOdds(metricPct(d, metric))));
        const teamHasInfinity = teamData.some(d => !isFinite(pctToOdds(metricPct(d, metric))));

        if (teamHasInfinity && lastFinite) {
          const lastFiniteIdx = teamData.indexOf(lastFinite);
          const firstInfinityPoint = teamData[lastFiniteIdx + 1];

          if (firstInfinityPoint) {
            const x0 = x(lastFinite.date);
            const x1 = x(firstInfinityPoint.date);
            const cy = y(oddsToAxisPos(pctToOdds(metricPct(lastFinite, metric))));
            const isWin = pctToOdds(metricPct(firstInfinityPoint, metric)) === Infinity;

            g.append('line')
              .attr('class', 'team-stub')
              .attr('data-team', team)
              .attr('x1', x0).attr('x2', x1)
              .attr('y1', cy).attr('y2', cy)
              .attr('stroke', teamColor(team))
              .attr('stroke-width', 2)
              .attr('stroke-dasharray', '4,3')
              .attr('opacity', 0.6);

            iconsToDraw.push({
              cx: x1, cy, isWin, team,
              d: firstInfinityPoint,
              title: `${team}: ${isWin ? '100% (locked)' : '0% (eliminated)'}`
            });
          }
        }
      }

      teamData.forEach(d => {
        const plottable = isValueMetric
          ? (d[metric] != null && isFinite(d[metric]))
          : isFinite(pctToOdds(metricPct(d, metric)));
        if (plottable) {
          const cy = isValueMetric ? y(d[metric]) : y(oddsToAxisPos(pctToOdds(metricPct(d, metric))));
          g.append('circle')
            .attr('class', 'team-dot')
            .attr('data-team', team)
            .attr('cx', x(d.date))
            .attr('cy', cy)
            .attr('r', 3.5)
            .attr('fill', teamColor(team))
            .attr('stroke', '#f5f5f5')
            .attr('stroke-width', 1.5)
            .style('cursor', 'pointer')
            .on('mousemove', function (event) {
              highlightTeam(team);
              showTooltip(tooltipHtml(team, d, metric), event);
            })
            .on('mouseleave', function () {
              clearHighlight();
              hideTooltip();
            });
        }
      });
    });

    // icons on top (odds metrics only)
    const seen = new Set();
    iconsToDraw
      .filter(ev => {
        const key = `${ev.team}-${ev.isWin}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .forEach(ev => {
        const iconG = g.append('g')
          .attr('class', 'team-icon')
          .attr('data-team', ev.team)
          .style('cursor', 'pointer')
          .on('mousemove', function (event) {
            highlightTeam(ev.team);
            showTooltip(tooltipHtml(ev.team, ev.d, metric), event);
          })
          .on('mouseleave', function () {
            clearHighlight();
            hideTooltip();
          });

        iconG.append('circle')
          .attr('class', 'icon-circle')
          .attr('cx', ev.cx).attr('cy', ev.cy).attr('r', 6)
          .attr('fill', teamColor(ev.team))
          .attr('stroke', '#fff')
          .attr('stroke-width', 1.5);
        iconG.append('text')
          .attr('class', 'icon-check')
          .attr('x', ev.cx).attr('y', ev.cy)
          .attr('dy', '0.32em').attr('text-anchor', 'middle')
          .attr('font-size', '8px').attr('font-weight', 'bold').attr('fill', '#fff')
          .style('pointer-events', 'none')
          .text(ev.isWin ? '\u2713' : '\u2715');
      });

    // legend
    const legendTeams = [...teams].sort((a, b) => {
      const aId = teamMatchupId.get(a);
      const bId = teamMatchupId.get(b);

      if (aId == null && bId == null) return d3.ascending(a, b);
      if (aId == null) return 1;
      if (bId == null) return -1;

      return d3.ascending(+aId, +bId) || d3.ascending(a, b);
    });

    const numTeams = teams.length;
    const itemSpacing = 20;
    const totalLegendHeight = numTeams * itemSpacing;

    const legend = svg.append('g')
      .attr('transform', `translate(${margin.left + innerWidth + 20},  ${margin.top + (innerHeight - totalLegendHeight) / 2})`);
    const legendRowHeight = 18;
    const pairGap = 8;
    const pairSize = 2;
    const legendLineWidth = 0;
    const legendSeparatorColor = 'rgba(0,0,0,0.12)';

    legendTeams.forEach((team, i) => {
      const row = legend.append('g')
        .attr('class', 'legend-row')
        .attr('data-team', team)
        .attr('transform', `translate(0, ${
          Math.floor(i / pairSize) * (pairSize * legendRowHeight + pairGap) +
          (i % pairSize) * legendRowHeight
        })`)
        .style('cursor', 'pointer')
        .on('mouseenter', function (event) {
          highlightTeam(team);
          const latest = latestPointByTeam.get(team);
          if (!latest) return;

          const rowY = Math.floor(i / pairSize) * (pairSize * legendRowHeight + pairGap) +
            (i % pairSize) * legendRowHeight;

          const fakeEvent = {
            clientX: event.clientX,
            clientY: event.clientY
          };

          // Prefer anchoring near legend; fallback to cursor-based placement in showTooltip
          showTooltip(tooltipHtml(team, latest, metric), fakeEvent);
          const [px, py] = d3.pointer(event, el);
          tooltip
            .style('left', `${px + 18}px`)
            .style('top', `${margin.top + rowY - 10}px`);
        })
        .on('mouseleave', () => {
          clearHighlight();
          hideTooltip();
        })

      row.append('rect')
        .attr('width', 10).attr('height', 10).attr('rx', 2)
        .attr('fill', teamColor(team));

      row.append('text')
        .attr('x', 16).attr('y', 9)
        .attr('font-size', 14)
        .attr('fill', teamColor(team))
        .text(team);

      if ((i + 1) % pairSize === 0 && i < legendTeams.length - 1) {
        const pairIndex = Math.floor(i / pairSize);
        const yAfterPair = (pairIndex + 1) * (pairSize * legendRowHeight + pairGap) - (pairGap / 2);

        legend.append('line')
          .attr('x1', 0)
          .attr('x2', legendLineWidth)
          .attr('y1', yAfterPair)
          .attr('y2', yAfterPair)
          .attr('stroke', legendSeparatorColor)
          .attr('stroke-width', 1);
      }
    });
  }

  metricSelect.on('change', render);

  render();

  return svg.node();
}
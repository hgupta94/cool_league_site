/**
 * createWarChart — renders a stacked bar chart of team WAR by position using D3.js
 *
 * @param {string|HTMLElement} container  CSS selector or DOM element to render into
 * @param {Array<{team_id: number|string, position: string, war: number}>} data
 *        One row per team per position. Positive `war` values stack upward from
 *        zero; negative values stack downward below zero.
 * @param {Object} [options]
 * @param {number} [options.width=640]              Total SVG width in px
 * @param {number} [options.height=400]             Total SVG height in px
 * @param {Object} [options.margin]                 {top, right, bottom, left}
 * @param {Array<string>} [options.positions]       Stacking order of positions (bottom to top)
 * @param {Object} [options.positionColors]         Optional {position: cssColor} map. Falls back
 *                                                   to a built-in palette for unknown positions.
 * @param {string} [options.teamLabel='Team']       Prefix used for x-axis tick labels ("Team 1", ...)
 * @returns {SVGSVGElement} the rendered <svg> node
 */

function createWarChart(container, data, options = {}) {
  const {
    width = 600,
    height = 400,
    margin = { top: 40, right: 100, bottom: 20, left: 44 },
    positions = ['RB', 'WR', 'QB', 'TE', 'DST'],
    positionColors = null,
  } = options;

  const el = typeof container === 'string' ? document.querySelector(container) : container;
  el.innerHTML = '';
  d3.select(el).style('position', 'relative');

  const defaultColors = {
    RB: '#378ADD',
    WR: '#D85A30',
    QB: '#1D9E75',
    TE: '#BA7517',
    DST: '#7F77DD'
  };
  const colorFor = pos => (positionColors && positionColors[pos]) || defaultColors[pos] || '#888887';

  const axisColor = 'rgba(0,0,0,0.2)';
  const textColor = 'rgba(0,0,0,0.5)';
  const gridColor = 'rgba(0,0,0,0.07)';

  // ---- aggregate rows into one object per team ----
  const teamIds = Array.from(new Set(data.map(d => d.team_id))).sort((a, b) => a - b);
  const teams = teamIds.map(id => {
    const row = { team_id: id };
    let total = 0;
    positions.forEach(p => {
      const rec = data.find(d => d.team_id === id && d.position === p);
      row[p] = rec ? rec.war : 0;
      total += row[p];
    });
    row.total = total;
    return row;
  });
  teams.sort((a, b) => b.total - a.total);

  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const svg = d3.select(el).append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('width', width)
    .attr('height', height)
    .style('display', 'block')
    .style('margin', '0 auto')
    .style('max-width', '100%')
    .style('overflow', 'visible');

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleBand()
    .domain(teams.map(d => `${d.team_id}`))
    .range([0, innerWidth])
    .padding(0.25);

  let yMinRaw = 0, yMaxRaw = 0;
  teams.forEach(t => {
    let pos = 0, neg = 0;
    positions.forEach(p => { if (t[p] >= 0) pos += t[p]; else neg += t[p]; });
    yMaxRaw = Math.max(yMaxRaw, pos);
    yMinRaw = Math.min(yMinRaw, neg);
  });
  const y = d3.scaleLinear().domain([yMinRaw * 1.35, yMaxRaw * 0.95]).nice().range([innerHeight, 0]);

  // gridlines
  g.append('g')
    .call(d3.axisLeft(y).ticks(6).tickSize(-innerWidth).tickFormat(''))
    .call(ax => ax.select('.domain').remove())
    .selectAll('line')
    .attr('stroke', 'rgba(0,0,0,0.1)')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', 0.65);

  // x-axis (labels sit below the plot area, clear of negative bars)
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(x).tickSize(0).tickPadding(-6))
    .call(ax => ax.select('.domain').remove())
    .selectAll('text')
    .attr('fill', textColor)
    .style('font-size', 12);

  // y-axis
  g.append('g')
    .call(d3.axisLeft(y).ticks(6))
    .call(ax => {
      ax.select('.domain').remove();
      ax.selectAll(".tick line").remove();
    })
    .selectAll('text')
    .attr('fill', textColor)
    .style('font-size', 12);

  // zero line
  g.append('line')
    .attr('x1', 0).attr('x2', innerWidth)
    .attr('y1', y(0)).attr('y2', y(0))
    .attr('stroke', 'rgba(0,0,0,0.1)')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', 0.65);

  // ---- tooltip ----
  const tooltip = d3.select(el).append('div')
    .attr('class', 'war-tooltip')
    .style('position', 'absolute')
    .style('z-index', '10')
    .style('background', 'rgba(255,255,255,0.95)')
    .style('border', '1px solid rgba(0,0,0,0.1)')
    .style('border-radius', '6px')
    .style('padding', '6px 10px')
    .style('box-sizing', 'border-box')
    .style('font-size', '13px')
    .style('color', 'rgba(0,0,0,0.7)')
    .style('pointer-events', 'none')
    .style('box-shadow', '0 2px 6px rgba(0,0,0,0.1)')
    .style('display', 'none');

  function showTooltip(html, event) {
    const [px, py] = d3.pointer(event, el);
    tooltip.style('display', 'block').html(html)
      .style('left', `${px + 14}px`)
      .style('top', `${py - 28}px`);
  }

  function hideTooltip() {
    tooltip.style('display', 'none');
  }

  // ---- build stacked segment data (fixed position order, split at zero) ----
  const barData = [];
  teams.forEach(t => {
    let posCum = 0, negCum = 0;
    positions.forEach(p => {
      const v = t[p];
      if (v >= 0) {
        barData.push({ team_id: t.team_id, key: p, y0: posCum, y1: posCum + v, value: v });
        posCum += v;
      } else {
        barData.push({ team_id: t.team_id, key: p, y0: negCum + v, y1: negCum, value: v });
        negCum += v;
      }
    });
  });

  g.selectAll('rect')
    .data(barData)
    .join('rect')
    .attr('x', d => x(`${d.team_id}`))
    .attr('y', d => y(Math.max(d.y0, d.y1)))
    .attr('height', d => Math.max(0, Math.abs(y(d.y0) - y(d.y1)) - 1.5))
    .attr('width', x.bandwidth())
    .attr('rx', 2)
    .attr('fill', d => colorFor(d.key))
    .style('cursor', 'pointer')
    .on('mousemove', function (event, d) {
      d3.select(this).attr('opacity', 0.75);
      showTooltip(`<strong style="color:${colorFor(d.key)}">${d.key}</strong><br>${d.value.toFixed(1)} WAR`, event);
    })
    .on('mouseleave', function () {
      d3.select(this).attr('opacity', 1);
      hideTooltip();
    });

  // legend
  const itemSpacing = 20;
  const totalLegendHeight = positions.length * itemSpacing;

  const legend = svg.append('g')
    .attr('transform', `translate(${margin.left + innerWidth + 15}, ${margin.top + (innerHeight - totalLegendHeight) / 2})`);

  positions.forEach((p, i) => {
    const gItem = legend.append('g')
      .attr('data-position', p)
      .attr('transform', `translate(0, ${i * itemSpacing})`)
      .style('cursor', 'pointer');

    gItem.append('rect')
      .attr('width', 10).attr('height', 10).attr('rx', 2)
      .attr('fill', colorFor(p));

    gItem.append('text')
      .attr('x', 17).attr('y', 10)
      .attr('font-size', 13)
      .attr('fill', colorFor(p))
      .text(p);
  });

  return svg.node();
}
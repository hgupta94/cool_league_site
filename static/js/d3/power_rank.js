/**
 * createLineChart — renders a multi-team line chart using D3.js
 *
 * @param {string|HTMLElement} container  CSS selector or DOM element to render into
 * @param {Array<{x: number, y: number, team: string}>} data
 * @param {Object} [options]
 * @param {number} [options.width=640]           Total SVG width in px
 * @param {Object} [options.margin]              {top, right, bottom, left}
 */
function createRankChart(container, data, options = {}) {
  const {
    width = 960,
    height = 1000,
    margin = {top:50, right:120, bottom:60, left:50},
  } = options;

  const isDark = matchMedia('(prefers-color-scheme: light)').matches;

  const addlColors = ['#20B2C8', '#9B59B6'];
  const colorMap = {
    'Aaro': '#378ADD',
    'Adit': '#1D9E75',
    'Aide': '#D85A30',
    'Aksh': '#7F77DD',
    'Arju': '#D4537E',
    'Char': '#BA7517',
    'Ayaz': '#639922',
    'Hirs': '#888780',
    'Nick': '#E07B39',
    'Varu': '#C0392B',
  };

  const teams = Array.from(new Set(data.map(d => d.team)));

  const grouped = d3.group(data, d => d.team);

  // Order legend by the y-value of each team's last point (descending)
  const teamsOrderedByLastY = [...grouped.entries()]
    .map(([team, pts]) => {
      const sorted = [...pts].sort((a, b) => a.week - b.week);
      return { team, lastY: sorted[sorted.length - 1].y };
    })
    .sort((a, b) => a.lastY - b.lastY)
    .map(d => d.team);

  const el = typeof container === 'string' ? document.querySelector(container) : container;
  el.innerHTML = '';

  const innerWidth  = width - margin.left - margin.right;
  const innerHeight = 300;
  const totalHeight = innerHeight + margin.top + margin.bottom;

  const allX = data.map(d => d.week);
  const allY = data.map(d => d.y);
  const xScale = d3.scaleLinear()
    .domain(d3.extent(allX))
    .nice()
    .range([0, innerWidth]);
  const yScale = d3.scaleLinear()
    .domain([1, d3.max(allY)])
    .range([0, innerHeight]);

  const svg = d3.select(el).append('svg')
    .attr('viewBox', `0 0 ${width} ${totalHeight}`)
    .attr('width', width)
    .attr('height', totalHeight)
    .style('overflow', 'visible');

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  // Grid lines
  const gridColor = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)';
  g.append('g')
    .call(d3.axisLeft(yScale).ticks(d3.max(allY)).tickSize(-innerWidth).tickFormat(''))
    .call(ax => ax.select('.domain').remove())
    .call(ax => ax.selectAll('line').attr('stroke', gridColor));

  // Axes
  const axisColor = isDark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.35)';
  const textColor = isDark ? 'rgba(255,255,255,0.55)' : 'rgba(0,0,0,0.5)';

  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(xScale).ticks(new Set(data.map(d => d.week)).size))
    .call(ax => ax.select('.domain').attr('stroke', axisColor))
    .call(ax => ax.selectAll('text').attr('fill', textColor).attr('font-size', 12));

  g.append('g')
    .call(d3.axisLeft(yScale).tickValues(d3.range(1, d3.max(allY) + 1)))
    .call(ax => ax.select('.domain').attr('stroke', axisColor))
    .call(ax => ax.selectAll('text').attr('fill', textColor).attr('font-size', 12));

  // Title
  svg.append('text')
  .attr('x', margin.left + innerWidth / 2)
  .attr('y', margin.top / 2)
  .attr('text-anchor', 'middle')
  .attr('font-size', 32)
  .attr('font-weight', 500)
  .attr('fill', 'rgba(0,0,0,0.7)')
  .text('Weekly Power Ranks');

  // X label
  svg.append('text')
  .attr('x', margin.left + innerWidth / 2)
  .attr('y', margin.top + innerHeight + margin.bottom - 15)
  .attr('text-anchor', 'middle')
  .attr('font-size', 16)
  .attr('fill', 'rgba(0,0,0,0.5)')
  .text('Week');

  // Y label
  svg.append('text')
  .attr('transform', `rotate(-90)`)
  .attr('x', -(margin.top + innerHeight / 2))
  .attr('y', 9)
  .attr('text-anchor', 'middle')
  .attr('font-size', 16)
  .attr('fill', 'rgba(0,0,0,0.5)')
  .text('Power Rank');

  // Line generator
  const line = d3.line()
    .x(d => xScale(d.week))
    .y(d => yScale(d.y))
    .curve(d3.curveMonotoneX);

  const lineGroups = {};

  teamsOrderedByLastY.forEach(team => {
    const pts = [...grouped.get(team)].sort((a, b) => a.week - b.week);
    const grp = g.append('g');

    const path = grp.append('path')
      .datum(pts)
      .attr('fill', 'none')
      .attr('stroke', colorMap[team])
      .attr('stroke-width', 2.5)
      .attr('d', line)
      .style('transition', 'stroke-width 0.15s ease, opacity 0.15s ease')
      .style('cursor', 'pointer');

    lineGroups[team] = path;

    // Dots at each data point
    grp.selectAll('circle')
      .data(pts)
      .join('circle')
      .attr('cx', d => xScale(d.week))
      .attr('cy', d => yScale(d.y))
      .attr('r', 3.5)
      .attr('fill', colorMap[team])
      .attr('stroke', isDark ? '#1a1a1a' : '#fff')
      .attr('stroke-width', 1.5)
      .style('pointer-events', 'none');
  });

  // Hover helpers
  function boldLine(team) {
    Object.entries(lineGroups).forEach(([t, path]) => {
      if (t === team) {
        path.attr('stroke-width', 4.5).style('opacity', 1);
      } else {
        path.attr('stroke-width', 2).style('opacity', 0.2);
      }
    });
    Object.entries(legendItems).forEach(([t, label]) => {
      label.style('opacity', t === team ? 1 : 0.2);
    });
  }

  function resetLines() {
    Object.values(lineGroups).forEach(path =>
      path.attr('stroke-width', 2.5).style('opacity', 1)
    );
    Object.values(legendItems).forEach(label =>
      label.style('opacity', 1)
    );
  }

  // Line hover
  const legendItems = {};

  Object.entries(lineGroups).forEach(([team, path]) => {
    path
      .on('mouseenter', () => {
        boldLine(team);
        legendItems[team]?.attr('font-weight', '800').attr('font-size', 15);
      })
      .on('mouseleave', () => {
        resetLines();
        Object.values(legendItems).forEach(el => el.attr('font-weight', '400').attr('font-size', 14));
      });
  });

  // Legend — labels at end of each line
  teamsOrderedByLastY.forEach(team => {
    const pts = [...grouped.get(team)].sort((a, b) => a.week - b.week);
    const lastPt = pts[pts.length - 1];

    const label = g.append('text')
      .attr('x', xScale(lastPt.week) + 8)
      .attr('y', yScale(lastPt.y))
      .attr('dy', '0.35em')
      .attr('font-size', 14)
      .attr('fill', colorMap[team])
      .text(team);

    legendItems[team] = label;

    label
      .on('mouseenter', () => {
        boldLine(team);
        label.attr('font-weight', '800').attr('font-size', 15);
      })
      .on('mouseleave', () => {
        resetLines();
        label.attr('font-weight', '400').attr('font-size', 14);
      });
  });
  return svg.node();
}
const width = 960;
const height = 570;
const svgNamespace = 'http://www.w3.org/2000/svg';
const radians = Math.PI / 180;
const number = new Intl.NumberFormat('en-US');

function albers(meridian, firstParallel, secondParallel) {
  const first = Math.sin(firstParallel * radians);
  const n = (first + Math.sin(secondParallel * radians)) / 2;
  const c = 1 + first * (2 * n - first);
  return ([longitude, latitude]) => {
    const relativeLongitude = ((longitude - meridian + 540) % 360) - 180;
    const angle = n * relativeLongitude * radians;
    const radius = Math.sqrt(c - 2 * n * Math.sin(latitude * radians)) / n;
    return [radius * Math.sin(angle), radius * Math.cos(angle)];
  };
}

function fittedProjection(entries, project, [left, top, availableWidth, availableHeight]) {
  const points = entries.flatMap(([, rings]) => rings.flatMap(ring => ring.map(project)));
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const scale = Math.min(availableWidth / (maxX - minX), availableHeight / (maxY - minY));
  const centerX = (minX + maxX) / 2, centerY = (minY + maxY) / 2;
  return coordinates => {
    const [x, y] = project(coordinates);
    return [left + availableWidth / 2 + (x - centerX) * scale, top + availableHeight / 2 + (y - centerY) * scale];
  };
}

function drawOutlines(svg, geometry) {
  const mainland = Object.entries(geometry).filter(([state]) => state !== 'AK' && state !== 'HI');
  const regions = [
    [mainland, albers(-96, 29.5, 45.5), [14, 10, 932, 530]],
    [[['AK', geometry.AK]], albers(-154, 55, 65), [30, 423, 215, 110]],
    [[['HI', geometry.HI]], albers(-157, 18, 22), [266, 456, 132, 77]],
  ];
  const projections = new Map();
  for (const [entries, project, bounds] of regions) {
    const transform = fittedProjection(entries, project, bounds);
    for (const [state, rings] of entries) {
      projections.set(state, transform);
      const path = document.createElementNS(svgNamespace, 'path');
      const outline = rings.map(ring => {
        const points = ring.map(coordinates => transform(coordinates).map(value => value.toFixed(1)).join(','));
        return `M${points.join('L')}Z`;
      });
      path.setAttribute('d', outline.join(' '));
      svg.append(path);
    }
  }
  for (const [label, x] of [['Alaska', 138], ['Hawaii', 332]]) {
    const caption = document.createElementNS(svgNamespace, 'text');
    caption.setAttribute('x', x);
    caption.setAttribute('y', 554);
    caption.textContent = label;
    svg.append(caption);
  }
  return projections;
}

function nearbyGroups(rinks, projections, distance) {
  const groups = [];
  for (const rink of rinks) {
    const project = projections.get(rink.state);
    if (!project || !Number.isFinite(rink.latitude) || !Number.isFinite(rink.longitude)) continue;
    const [x, y] = project([rink.longitude, rink.latitude]);
    const nearby = groups.find(group => Math.hypot(group.x - x, group.y - y) < distance);
    if (nearby) {
      nearby.rinks.push(rink);
    } else {
      groups.push({x, y, rinks: [rink]});
    }
  }
  return groups;
}

function drawDetails(details, group) {
  details.replaceChildren();
  details.hidden = !group;
  if (!group) return;
  const title = document.createElement('h3');
  const cities = new Set(group.rinks.map(rink => `${rink.city}, ${rink.state}`));
  title.textContent = cities.size === 1 ? [...cities][0] : `${number.format(group.rinks.length)} nearby rinks`;
  const list = document.createElement('ul');
  for (const rink of group.rinks) {
    const item = document.createElement('li');
    const name = document.createElement('strong');
    name.textContent = rink.name;
    const description = document.createElement('span');
    description.textContent = `${rink.city}, ${rink.state} · ${number.format(rink.games)} ${rink.games === 1 ? 'game' : 'games'}`;
    item.append(name, description);
    list.append(item);
  }
  details.append(title, list);
}

export function createRinkMap() {
  const frame = document.getElementById('map-frame');
  const svg = document.getElementById('map-outlines');
  const markers = document.getElementById('map-markers');
  const summary = document.getElementById('map-summary');
  const details = document.getElementById('map-details');
  let projections;
  let loading;
  let rinks = [];
  let selectedRink;

  function render() {
    if (!projections) return;
    const groups = nearbyGroups(rinks, projections, 25 * width / Math.max(frame.clientWidth, 280));
    const mapped = groups.flatMap(group => group.rinks);
    const states = new Set(mapped.map(rink => rink.state));
    const missing = rinks.length - mapped.length;
    if (mapped.length) {
      summary.textContent = `${number.format(mapped.length)} ${mapped.length === 1 ? 'rink' : 'rinks'} in ${states.size} ${states.size === 1 ? 'state' : 'states'}. Select a marker for details.`;
    } else {
      summary.textContent = rinks.length ? 'This selection has no mapped rink locations.' : 'No games match these filters.';
    }
    if (missing && mapped.length) summary.append(` ${number.format(missing)} ${missing === 1 ? 'rink needs' : 'rinks need'} a map location.`);
    const active = groups.find(group => group.rinks.some(rink => rink.name === selectedRink));
    drawDetails(details, active);
    const buttons = groups.map(group => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'map-marker';
      button.style.left = `${group.x / width * 100}%`;
      button.style.top = `${group.y / height * 100}%`;
      button.textContent = group.rinks.length > 1 ? group.rinks.length : '';
      const label = group.rinks.length > 1 ? `${group.rinks.length} rinks near ${group.rinks[0].city}, ${group.rinks[0].state}` : `${group.rinks[0].name} · ${group.rinks[0].city}, ${group.rinks[0].state}`;
      button.title = label;
      button.setAttribute('aria-label', label);
      button.setAttribute('aria-controls', 'map-details');
      button.setAttribute('aria-pressed', group === active);
      button.addEventListener('click', () => {
        selectedRink = group.rinks[0].name;
        for (const marker of markers.children) marker.setAttribute('aria-pressed', marker === button);
        drawDetails(details, group);
      });
      return button;
    });
    markers.replaceChildren(...buttons);
  }

  return (rankedRinks, locations) => {
    rinks = rankedRinks.map(rink => ({...rink, ...locations[rink.name]}));
    if (projections) {
      render();
    } else if (!loading) {
      summary.textContent = 'Loading rink map…';
      loading = fetch(new URL('assets/us-states.json', import.meta.url))
        .then(response => {
          if (!response.ok) throw new Error('State boundaries could not be loaded.');
          return response.json();
        })
        .then(geometry => {
          projections = drawOutlines(svg, geometry);
          frame.hidden = false;
          render();
          new ResizeObserver(render).observe(frame);
        })
        .catch(() => {
          summary.textContent = 'The map is unavailable. Rink locations are listed in the rink filter.';
        });
    }
  };
}

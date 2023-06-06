// index.js

// Initial configuration
const width = 800;
const heightPerLayer = 20;

// Define the scales
const xScale = d3.scaleLinear().range([0, width]);

// Fetch the data from the server
fetch('/config')
    .then(response => response.json())
    .then(data => {
        data.sort((a, b) => a.start - b.start); // Sort by start time

        // Assign each clip to a layer
        for (let i = 1; i < data.length; i++) {
            let layer = 0;

            for (let j = 0; j < i; j++) {
                const previous = data[j];

                if (data[i].start < previous.end) {
                    layer = Math.max(layer, previous.layer + 1);
                }
            }

            data[i].layer = layer;
        }

        // Update the domain of the xScale
        xScale.domain([0, d3.max(data, d => d.end)]);

        // Create the SVG
        const svg = d3.select('#timeline')
            .attr('width', width)
            .attr('height', (data.length + 1) * heightPerLayer); // Adjust the height based on the number of clips

        // Draw the clips
        svg.selectAll('.clip')
            .data(data)
            .enter().append('rect')
            .attr('class', 'clip')
            .attr('x', d => xScale(d.start))
            .attr('y', (d, i) => (i + 1) * heightPerLayer)
            .attr('width', d => xScale(d.end - d.start))
            .attr('height', heightPerLayer - 1)
            .style('fill', () => getRandomColor());

        // Draw the clip titles
        svg.selectAll('.clip-name')
            .data(data)
            .enter().append('text')
            .attr('class', 'clip-name')
            .attr('x', d => xScale(d.start))
            .attr('y', (d, i) => (i + 1) * heightPerLayer + heightPerLayer / 2)
            .attr('dy', '0.35em')
            .text(d => d.name);
    });

// Helper function to generate a random color
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

async function draw(complexity) {
    d3.select("#chart").selectAll("*").remove();
    const treeData = await fetch(`/api/bom/${complexity}/`).then(r=>r.json());
    
    const width=960, height=600;
    const svg = d3.select("#chart")
                  .attr("width",width).attr("height",height)
                  .append("g").attr("transform","translate(40,0)");
  
    const root = d3.hierarchy(treeData, d=>d.children);
    const treeLayout = d3.tree().size([height, width - 160]);
    treeLayout(root);
  
    // Links
    svg.selectAll('path.link')
      .data(root.links())
      .enter().append('path')
        .attr('class','link')
        .attr('d', d3.linkHorizontal()
                      .x(d=>d.y).y(d=>d.x))
        .attr('stroke','#555').attr('fill','none');
  
    // Nodes
    const node = svg.selectAll('g.node')
        .data(root.descendants())
        .enter().append('g')
          .attr('class', 'node')
          .attr('transform', d=>`translate(${d.y},${d.x})`);
  
    node.append('circle')
        .attr('r', d=> d.data.level===0 ? 8 : 4)
        .attr('fill', d=> d.data.level===0 ? '#1f77b4' : '#ff7f0e');
  
    node.append('text')
        .attr('dy', 3).attr('x', d=> d.children ? -10 : 10)
        .style('text-anchor', d=> d.children ? 'end' : 'start')
        .text(d=>`${d.data.item_no} ($${d.data.cost.toFixed(2)})`);
  }
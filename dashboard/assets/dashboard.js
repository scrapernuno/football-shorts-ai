async function loadDashboard() {


const response = await fetch(
"data/dashboard_model.json"
);


const data = await response.json();



document.getElementById(
"status"
).innerHTML = `

ONLINE<br>

${data.generated_at}

`;



renderTop(data);

renderMetrics(data);

renderHooks(data);

renderRanking(data);

renderStoryboard(data);

renderAssets(data);

}



function renderTop(data){


document.getElementById(
"top-short"
).innerHTML = `

<h3>
${data.top_title}
</h3>


<p>
${data.top_hook}
</p>


<strong>
Viral Probability:
${data.viral_probability}%
</strong>

`;

}




function renderMetrics(data){


const m=data.metrics;


document.getElementById(
"metrics"
).innerHTML = `

<p>
Views:
${m.predicted_views_low}
-
${m.predicted_views_high}
</p>


<p>
Confidence:
${m.confidence_score}%
</p>


<p>
Comments:
${m.predicted_comment_rate_percent}%
</p>

`;

}





function renderHooks(data){


document.getElementById(
"hooks"
).innerHTML = `


<p>
${data.hooks.primary}
</p>


<ul>

${
data.hooks.alternatives
.map(
h=>`<li>${h}</li>`
)
.join("")
}

</ul>


`;

}




function renderRanking(data){


document.getElementById(
"ranking"
).innerHTML =


data.ranking.map(
item=>`

<div class="ranking-item">

<b>
#${item.priority}
</b>

${item.title}

<br>

${item.viral_probability}%


</div>

`
).join("");

}





function renderStoryboard(data){


document.getElementById(
"storyboard"
).innerHTML =


data.storyboard.map(
scene=>`

<div class="scene">


<b>
Scene ${scene.scene_number}
</b>


<p>
${scene.visual_description}
</p>


<span>
${scene.start_second}s -
${scene.end_second}s
</span>


</div>


`
).join("");


}





function renderAssets(data){


document.getElementById(
"assets"
).innerHTML = `

<p>
Asset planning disponível no editorial package.
</p>

`;

}



loadDashboard();


// add an onclick listener to the submit button that sends an API request to my backend containing the user's input
document.getElementById("submit").addEventListener("click", function() {
    // Show the loading spinner
    var loadingElement = document.getElementById("loading");
    var results = document.getElementById("results");
    var embedding = document.getElementById("response-embedding")
    results.classList.add("hidden");
    loadingElement.classList.remove("hidden");
    embedding.classList.add("hidden");

    console.log("button clicked");
    let input = document.getElementById("input").value;
    let url = "http://localhost:8080/api/" + input;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            let top_k = data.top_k
            let response_embedding = data.response_embedding
            //extract the "metadata" element from each item in the top_k list
            let metadata = top_k.map(item => item.metadata);
            let scores = top_k.map(item => parseFloat(item.score).toFixed(2));
            //extract the "text" element from each item in the metadata list
            let neighbors = metadata.map(item => item.text);
            //display the neighbors in the neighbors table along with a hyperlink
            //each hyperlink is a link to google search with the exact text of the neighbor in quotes
            // the hyperlink appears as a footnote with the number corresponding to the row in the table
            let table = document.getElementById("neighbors");
            //clear the table
            table.innerHTML = "";
            //add a row for each neighbor
            for (let i = 0; i < neighbors.length; i++) {
                let row = table.insertRow(i);
                let cell = row.insertCell(0);
                cell.innerHTML = `${neighbors[i]} <a href='https://www.google.com/search?q="${neighbors[i]}"' target='_blank'>[${i+1}]</a> <span class="score">(score: ${scores[i]})</span>`;
            }
            
            //display the response text
            document.getElementById("response-text").innerHTML = data.response_text;
            console.log(data);

            //display the response embedding. response embedding is a list of 384 numbers. Display the first 10 rounded to 4 decimal places,
            // three dots, then display the last 10 rounded to 4 decimal places
            let response_embedding_string = "[" + response_embedding.slice(0, 10).map(item => parseFloat(item).toFixed(4)).join(", ") + " . . . " + response_embedding.slice(-10).map(item => parseFloat(item).toFixed(4)).join(", ") + "]";
            embedding.innerHTML = response_embedding_string;

            results.classList.remove("hidden");
            loadingElement.classList.add("hidden");
            embedding.classList.remove("hidden");
        });
});


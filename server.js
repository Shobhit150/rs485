import express from "express"

const app = express()
app.use(express.json())

app.post("/log", (req, res) => {
  console.log("Received payload:", req.body)

  res.json({
    status: "success",
    received: req.body
  })
})

app.listen(3000, () => {
  console.log("Test API running on http://localhost:3000")
})
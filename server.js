require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const authRoutes = require('./routes/auth');

const app = express();

app.use(cors());
app.use(express.json());

app.get('/api/health', function(req, res) {
res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use('/api', authRoutes);

app.use(function(err, req, res, next) {
console.error('Unhandled error:', err);
res.status(500).json({
success: false,
message: 'Internal server error',
error: process.env.NODE_ENV === 'production' ? 'Something went wrong' : err.message
});
});

const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/student_auth';

mongoose
.connect(MONGODB_URI)
.then(function() {
console.log('Connected to MongoDB');
app.listen(PORT, function() {
console.log('Server running on port ' + PORT);
});
})
.catch(function(err) {
console.error('MongoDB connection error:', err);
process.exit(1);
});

module.exports = app;
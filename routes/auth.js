const express = require('express');
const jwt = require('jsonwebtoken');
const { body, validationResult } = require('express-validator');
const User = require('../models/User');

const router = express.Router();

function generateToken(userId) {
return jwt.sign({ id: userId }, process.env.JWT_SECRET, { expiresIn: '7d' });
}

router.post(
'/signup',
[
body('name').trim().notEmpty().withMessage('Name is required').isLength({ min: 2, max: 50 }).withMessage('Name must be between 2 and 50 characters'),
body('email').trim().isEmail().withMessage('Please provide a valid email').normalizeEmail(),
body('password').isLength({ min: 6 }).withMessage('Password must be at least 6 characters'),
body('student_id').trim().notEmpty().withMessage('Student ID is required')
],
async function(req, res) {
try {
const errors = validationResult(req);
if (!errors.isEmpty()) {
return res.status(400).json({
success: false,
message: 'Validation failed',
errors: errors.array().map(function(e) {
return { field: e.path, message: e.msg };
})
});
}

const { name, email, password, student_id } = req.body;

const existingUser = await User.findOne({
$or: [{ email: email }, { student_id: student_id }]
});

if (existingUser) {
if (existingUser.email === email) {
return res.status(409).json({
success: false,
message: 'User already exists',
error: 'An account with this email already exists'
});
}
return res.status(409).json({
success: false,
message: 'User already exists',
error: 'An account with this student ID already exists'
});
}

const user = await User.create({
name: name,
email: email,
password: password,
student_id: student_id
});

const token = generateToken(user._id);

res.status(201).json({
success: true,
message: 'Signup successful',
data: {
user: {
id: user._id,
name: user.name,
email: user.email,
student_id: user.student_id
},
token: token
}
});
} catch (err) {
if (err.code === 11000) {
const field = Object.keys(err.keyValue)[0];
return res.status(409).json({
success: false,
message: 'User already exists',
error: 'An account with this ' + field + ' already exists'
});
}
console.error('Signup error:', err);
res.status(500).json({
success: false,
message: 'Internal server error',
error: 'Something went wrong. Please try again later.'
});
}
}
);

router.post(
'/login',
[
body('email').trim().isEmail().withMessage('Please provide a valid email').normalizeEmail(),
body('password').notEmpty().withMessage('Password is required')
],
async function(req, res) {
try {
const errors = validationResult(req);
if (!errors.isEmpty()) {
return res.status(400).json({
success: false,
message: 'Validation failed',
errors: errors.array().map(function(e) {
return { field: e.path, message: e.msg };
})
});
}

const { email, password } = req.body;

const user = await User.findOne({ email: email }).select('+password');

if (!user) {
return res.status(401).json({
success: false,
message: 'Invalid credentials',
error: 'No account found with this email'
});
}

const isMatch = await user.comparePassword(password);

if (!isMatch) {
return res.status(401).json({
success: false,
message: 'Invalid credentials',
error: 'Incorrect password'
});
}

const token = generateToken(user._id);

res.status(200).json({
success: true,
message: 'Login successful',
data: {
user: {
id: user._id,
name: user.name,
email: user.email,
student_id: user.student_id
},
token: token
}
});
} catch (err) {
console.error('Login error:', err);
res.status(500).json({
success: false,
message: 'Internal server error',
error: 'Something went wrong. Please try again later.'
});
}
}
);

module.exports = router;
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema(
{
name: {
type: String,
required: [true, 'Name is required'],
trim: true,
minlength: 2,
maxlength: 50
},
email: {
type: String,
required: [true, 'Email is required'],
unique: true,
lowercase: true,
trim: true,
match: [/^\S+@\S+.\S+$/, 'Please provide a valid email']
},
password: {
type: String,
required: [true, 'Password is required'],
minlength: 6,
select: false
},
student_id: {
type: String,
required: [true, 'Student ID is required'],
unique: true,
trim: true
}
},
{
timestamps: true
}
);

userSchema.pre('save', async function (next) {
if (!this.isModified('password')) return next();
const salt = await bcrypt.genSalt(12);
this.password = await bcrypt.hash(this.password, salt);
next();
});

userSchema.methods.comparePassword = async function (candidatePassword) {
return await bcrypt.compare(candidatePassword, this.password);
};

userSchema.methods.toJSON = function () {
const obj = this.toObject();
delete obj.password;
delete obj.__v;
return obj;
};

module.exports = mongoose.model('User', userSchema);
create table Valve (
	id int auto_increment primary key,
	state int not null,
	created timestamp not null default current_timestamp
);

create table Timer (
	id int auto_increment primary key,
	start_time time not null,
	end_time time not null,
	created	timestamp not null default current_timestamp
);

create table WaterFlow (
	id int auto_increment primary key,
	flow float not null,
	created timestamp not null default current_timestamp
);

create table ValveJob (
	id int auto_increment primary key,
	status int not null default 0,
	updated timestamp not null default current_timestamp on update current_timestamp,	
	created timestamp not null default current_timestamp
);

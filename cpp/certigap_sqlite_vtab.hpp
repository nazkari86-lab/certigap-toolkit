#pragma once

struct sqlite3;

int certigap_register_vtab(sqlite3* database, char** error);

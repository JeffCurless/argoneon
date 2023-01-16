import logging

LOGGING_FILE ='/var/log/argoneon.log'
FORMAT_STRING='%(asctime)s %(process)d [%(levelname)s] %(message)s'
DATE_FORMAT='%b %d %y %H:%M:%S'
#
#
#
def enableLogging( enableDebug : bool = False ):
    if enableDebug:
        logging.basicConfig( filename=LOGGING_FILE,
                             filemode='a',
                             level=logging.DEBUG,
                             format=FORMAT_STRING,
                             datefmt=DATE_FORMAT)
    else:
        logging.basicConfig( filename=LOGGING_FILE,
                             filemode='a',
                             level=logging.INFO,
                             format=FORMAT_STRING,
                             datefmt=DATE_FORMAT)

#
#
#
def logDebug( message ):
    logging.debug( message )

#
#
#
def logInfo( message ):
    logging.info( message )

#
#
#
def logWarning( message ):
    logging.warning( message )

#
#
#
def logError( message ):
    logging.error( message )


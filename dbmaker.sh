#!/bin/sh
mysqladmin -hsql -umlab -pmlab create mlabdata <<EOF
mysql -hsql -umlab -pmlab mlabdata <<EOF
-- MySQL dump 10.13  Distrib 5.5.35, for debian-linux-gnu (x86_64)
--
-- Host: sql    Database: mlabdata
-- ------------------------------------------------------
-- Server version	5.1.73-0ubuntu0.10.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `attachment`
--

DROP TABLE IF EXISTS `attachment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `attachment` (
  `attachmentID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(255) DEFAULT NULL,
  `user` varchar(10) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `type` varchar(255) DEFAULT NULL,
  `note` text,
  `srctable` varchar(20) DEFAULT NULL,
  `srcID` int(11) unsigned NOT NULL,
  `data` longblob,
  `locked` int(11) DEFAULT NULL,
  `tags` varchar(1024) DEFAULT NULL,
  `lastmod` varchar(255) DEFAULT NULL,
  UNIQUE KEY `attachmentID` (`attachmentID`)
) ENGINE=MyISAM AUTO_INCREMENT=222 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dfile`
--

DROP TABLE IF EXISTS `dfile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `dfile` (
  `dfileID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `exper` varchar(10) DEFAULT NULL,
  `animal` varchar(10) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `user` varchar(10) DEFAULT NULL,
  `src` varchar(255) DEFAULT NULL,
  `filetype` varchar(20) DEFAULT NULL,
  `latency` float DEFAULT NULL,
  `winsize` float DEFAULT NULL,
  `crap` int(11) DEFAULT NULL,
  `preferred` int(11) DEFAULT NULL,
  `note` text,
  `attachlist` varchar(255) DEFAULT NULL,
  `locked` int(11) DEFAULT NULL,
  `tags` varchar(1024) DEFAULT NULL,
  `lastmod` varchar(255) DEFAULT NULL,
  UNIQUE KEY `dfileID` (`dfileID`),
  UNIQUE KEY `src` (`src`)
) ENGINE=MyISAM AUTO_INCREMENT=17698 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exper`
--

DROP TABLE IF EXISTS `exper`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exper` (
  `experID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `exper` varchar(10) DEFAULT NULL,
  `animal` varchar(10) DEFAULT NULL,
  `dir` varchar(255) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `time` varchar(11) DEFAULT NULL,
  `note` text,
  `locked` int(11) DEFAULT NULL,
  `deleted` int(11) DEFAULT NULL,
  `tags` varchar(1024) DEFAULT NULL,
  `lastmod` varchar(255) DEFAULT NULL,
  UNIQUE KEY `experID` (`experID`)
) ENGINE=MyISAM AUTO_INCREMENT=3436 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `session`
--

DROP TABLE IF EXISTS `session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `session` (
  `sessionID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `animal` varchar(10) DEFAULT NULL,
  `user` varchar(10) DEFAULT NULL,
  `computer` varchar(40) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `restricted` int(11) DEFAULT NULL,
  `tested` int(11) DEFAULT NULL,
  `water_work` int(11) DEFAULT NULL,
  `water_sup` int(11) DEFAULT NULL,
  `dtb` double DEFAULT NULL,
  `dtb_ml` double DEFAULT NULL,
  `xdtb` double DEFAULT NULL,
  `xdtb_ml` double DEFAULT NULL,
  `fruit` varchar(255) DEFAULT NULL,
  `fruit_ml` int(11) DEFAULT NULL,
  `totalfluid` double DEFAULT NULL,
  `food` int(11) DEFAULT NULL,
  `weight` double DEFAULT NULL,
  `thweight` double DEFAULT NULL,
  `ncorrect` int(11) DEFAULT NULL,
  `ntrials` int(11) DEFAULT NULL,
  `note` text,
  `locked` int(11) DEFAULT NULL,
  `tags` varchar(1024) DEFAULT NULL,
  `lastmod` varchar(255) DEFAULT NULL,
  UNIQUE KEY `noteID` (`sessionID`)
) ENGINE=MyISAM AUTO_INCREMENT=4380 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `unit`
--

DROP TABLE IF EXISTS `unit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `unit` (
  `unitID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `experID` int(10) unsigned DEFAULT NULL,
  `exper` varchar(10) DEFAULT NULL,
  `unit` varchar(10) DEFAULT NULL,
  `animal` varchar(10) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `well` varchar(11) DEFAULT NULL,
  `wellloc` varchar(255) DEFAULT NULL,
  `area` varchar(10) DEFAULT NULL,
  `hemi` char(1) DEFAULT NULL,
  `depth` int(11) DEFAULT NULL,
  `qual` float DEFAULT NULL,
  `rfx` float DEFAULT NULL,
  `rfy` float DEFAULT NULL,
  `rfr` float DEFAULT NULL,
  `latency` float DEFAULT NULL,
  `ori` float DEFAULT NULL,
  `color` varchar(20) DEFAULT NULL,
  `crap` int(11) DEFAULT NULL,
  `note` text,
  `locked` int(11) DEFAULT NULL,
  `tags` varchar(1024) DEFAULT NULL,
  `lastmod` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`unitID`),
  UNIQUE KEY `unitID` (`unitID`)
) ENGINE=MyISAM AUTO_INCREMENT=1639 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2014-03-10 16:37:00
EOF

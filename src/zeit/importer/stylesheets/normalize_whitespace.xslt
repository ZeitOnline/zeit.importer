<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:f="http://namespaces.zeit.de/functions" version="1.0">
    <xsl:output indent="yes" encoding="UTF-8" method="xml"/>

    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="*|@*|text()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="p/text()">
        <xsl:value-of select="f:normalize_and_strip_whitespace(.)" />
    </xsl:template>

    <xsl:template match="text()">
        <xsl:value-of select="f:normalize_whitespace(.)" />
    </xsl:template>

    <xsl:template match="text()[following-sibling::* and not(./preceding-sibling::*) and parent::p]">
        <xsl:value-of select="f:normalize_whitespace_strip_left(.)" />
    </xsl:template>

    <xsl:template match="text()[following-sibling::* and ./preceding-sibling::*]">
        <xsl:value-of select="f:normalize_whitespace(.)" />
    </xsl:template>

    <xsl:template match="text()[preceding-sibling::* and not(following-sibling::*) and parent::p]">
        <xsl:value-of select="f:normalize_whitespace_strip_right(.)" />
    </xsl:template>
</xsl:stylesheet>
